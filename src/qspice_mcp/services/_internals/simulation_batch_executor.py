"""Execution helpers for simulation sweep batches."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Protocol

from .simulation_batch_manifest import build_run_paths
from .simulation_batch_models import SimulationBatchRun, SweepKind

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol
    from qspice_mcp.services.simulation.generate_netlist import GeneratedNetlist
    from qspice_mcp.services.simulation.run_simulation import SimulationRun


class _OpenSchematicEditor(Protocol):
    def __call__(
        self,
        raw_path: str | Path,
        *,
        workspace_root: Path,
    ) -> tuple[_QschEditorProtocol, Path, str]:
        """Open one schematic editor instance."""


class _SaveEditedSchematic(Protocol):
    def __call__(
        self,
        editor: _QschEditorProtocol,
        *,
        schematic_path: Path,
        workspace_root: Path,
        output_path: str | Path | None,
    ) -> Path:
        """Persist one edited schematic variant."""


class _GenerateNetlistFn(Protocol):
    def __call__(
        self,
        raw_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
    ) -> GeneratedNetlist:
        """Generate one derived netlist."""


class _RunSimulationFn(Protocol):
    def __call__(
        self,
        netlist_path: str | Path,
        *,
        workspace_root: Path,
        settings: QSpiceSettings | None = None,
        dry_run: bool = False,
        timeout_s: float | None = None,
        log_path: str | Path | None = None,
        raw_output_path: str | Path | None = None,
        extra_switches: tuple[str, ...] = (),
        ascii_raw: bool = False,
    ) -> SimulationRun:
        """Run or plan one simulation."""


def execute_sweep_run(
    *,
    source_path: Path,
    workspace_root: Path,
    settings: QSpiceSettings | None,
    output_root: Path,
    index: int,
    label: str,
    assignment: Mapping[str, object],
    edit_kind: SweepKind,
    apply_edit: Callable[[_QschEditorProtocol], None],
    dry_run: bool,
    timeout_s: float | None,
    extra_switches: tuple[str, ...],
    ascii_raw: bool,
    open_editor: _OpenSchematicEditor,
    save_schematic: _SaveEditedSchematic,
    generate_netlist_fn: _GenerateNetlistFn,
    run_simulation_fn: _RunSimulationFn,
    save_run_record: Callable[[SimulationBatchRun], Path],
) -> SimulationBatchRun:
    """Create one edited schematic variant, then generate and run it."""

    del edit_kind
    workspace = workspace_root.resolve(strict=False)
    edited_schematic_path, netlist_path, log_path, raw_path = build_run_paths(
        source_path,
        output_root=output_root,
        index=index,
        label=label,
    )
    editor, resolved_source, _ = open_editor(source_path, workspace_root=workspace)
    apply_edit(editor)
    saved_schematic = save_schematic(
        editor,
        schematic_path=resolved_source,
        workspace_root=workspace,
        output_path=edited_schematic_path,
    )
    generated = generate_netlist_fn(
        saved_schematic,
        workspace_root=workspace,
        output_path=netlist_path,
    )
    simulation = run_simulation_fn(
        generated.netlist_path,
        workspace_root=workspace,
        settings=settings,
        dry_run=dry_run,
        timeout_s=timeout_s,
        log_path=log_path,
        raw_output_path=raw_path,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
    )
    run = SimulationBatchRun(
        index=index,
        label=label,
        assignment=dict(assignment),
        schematic_path=saved_schematic,
        netlist_path=simulation.netlist_path,
        log_path=simulation.log_path,
        raw_path=simulation.raw_path,
        command=simulation.command,
        dry_run=simulation.dry_run,
        exit_code=simulation.exit_code,
        duration_s=simulation.duration_s,
        warnings=tuple(generated.warnings),
    )
    save_run_record(run)
    return run


def execute_sweep_runs_in_parallel(
    *,
    source_path: Path,
    workspace_root: Path,
    settings: QSpiceSettings | None,
    output_root: Path,
    run_defs: Sequence[
        tuple[int, str, Mapping[str, object], SweepKind, Callable[[_QschEditorProtocol], None]]
    ],
    max_workers: int,
    dry_run: bool,
    timeout_s: float | None,
    extra_switches: tuple[str, ...],
    ascii_raw: bool,
    open_editor: _OpenSchematicEditor,
    save_schematic: _SaveEditedSchematic,
    generate_netlist_fn: _GenerateNetlistFn,
    run_simulation_fn: _RunSimulationFn,
    save_run_record: Callable[[SimulationBatchRun], Path],
    should_cancel: Callable[[], bool] | None = None,
    on_run_complete: Callable[[SimulationBatchRun], None] | None = None,
) -> tuple[list[SimulationBatchRun], list[str]]:
    """Execute independent sweep runs in parallel using a thread pool."""

    runs_by_index: dict[int, SimulationBatchRun] = {}
    run_defs_by_index = {index: (label, assignment) for index, label, assignment, _, _ in run_defs}
    warnings: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index: dict[Future[SimulationBatchRun], int] = {}

        for index, label, assignment, edit_kind, apply_edit in run_defs:
            if should_cancel is not None and should_cancel():
                warnings.append("Batch execution was canceled before all requested runs started.")
                break
            future = executor.submit(
                execute_sweep_run,
                source_path=source_path,
                workspace_root=workspace_root,
                settings=settings,
                output_root=output_root,
                index=index,
                label=label,
                assignment=assignment,
                edit_kind=edit_kind,
                apply_edit=apply_edit,
                dry_run=dry_run,
                timeout_s=timeout_s,
                extra_switches=extra_switches,
                ascii_raw=ascii_raw,
                open_editor=open_editor,
                save_schematic=save_schematic,
                generate_netlist_fn=generate_netlist_fn,
                run_simulation_fn=run_simulation_fn,
                save_run_record=save_run_record,
            )
            future_to_index[future] = index

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                run = future.result()
                runs_by_index[index] = run
                if on_run_complete is not None:
                    on_run_complete(run)
            except Exception as exc:
                warnings.append(f"Run {index} failed: {exc}")
                label, assignment = run_defs_by_index[index]
                run_paths = build_run_paths(
                    source_path,
                    output_root=output_root,
                    index=index,
                    label=label,
                )
                runs_by_index[index] = SimulationBatchRun(
                    index=index,
                    label=label,
                    assignment=dict(assignment),
                    schematic_path=run_paths[0],
                    netlist_path=run_paths[1],
                    log_path=run_paths[2],
                    raw_path=run_paths[3],
                    command=(),
                    dry_run=dry_run,
                    exit_code=-1,
                    warnings=(str(exc),),
                )
                save_run_record(runs_by_index[index])

    sorted_runs = sorted(runs_by_index.values(), key=lambda run: run.index)
    return sorted_runs, warnings


__all__ = ["execute_sweep_run", "execute_sweep_runs_in_parallel"]
