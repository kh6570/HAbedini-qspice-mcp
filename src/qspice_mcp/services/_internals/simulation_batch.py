"""Shared helpers for synchronous simulation sweep services."""

from __future__ import annotations

import threading
from datetime import datetime
from typing import TYPE_CHECKING

from qspice_mcp.infra.progress import report_progress
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.run_simulation import run_simulation

from .simulation_batch_executor import (
    execute_sweep_run as _execute_sweep_run_impl,
)
from .simulation_batch_executor import (
    execute_sweep_runs_in_parallel as _execute_sweep_runs_in_parallel_impl,
)
from .simulation_batch_manifest import (
    _build_batch_snapshot,
    batch_manifest_path,
    batch_run_record_path,
    build_run_paths,
    load_batch_manifest,
    load_batch_run_record,
    save_batch_manifest,
    save_batch_run_record,
    slugify,
)
from .simulation_batch_models import (
    BatchState,
    ResumableBatchState,
    RetainedArtifactPolicy,
    SimulationBatch,
    SimulationBatchRun,
    SweepKind,
)
from .simulation_batch_retention import (
    _normalize_retained_artifact_policy,
    _prepare_retained_artifacts,
    load_resumable_batch_state,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


def validate_sweep_source(
    raw_path: str | Path,
    *,
    workspace_root: Path,
) -> Path:
    """Resolve and validate the current supported sweep source kind."""

    source_path = validate_existing_file(
        raw_path,
        workspace_root=workspace_root,
        suffixes=(".qsch", ".net", ".cir"),
    )
    if source_path.suffix.lower() != ".qsch":
        raise ValueError(
            "Sweep services currently require a .qsch source path because "
            "clean-room netlist editing is not implemented yet."
        )
    return source_path


def resolve_sweep_output_root(
    output_dir: str | Path | None,
    *,
    workspace_root: Path,
    source_path: Path,
    sweep_kind: SweepKind,
) -> Path:
    """Resolve the root directory used for one sweep batch."""

    if output_dir is not None:
        return resolve_workspace_path(output_dir, workspace_root=workspace_root)
    return (
        workspace_root
        / "artifacts"
        / "sweeps"
        / f"{slugify(source_path.stem)}-{slugify(sweep_kind)}"
    ).resolve(strict=False)


def _execute_pending_runs_sequentially(
    *,
    source_path: Path,
    workspace_root: Path,
    settings: QSpiceSettings | None,
    output_root: Path,
    pending_run_defs: Sequence[
        tuple[int, str, Mapping[str, object], SweepKind, Callable[[_QschEditorProtocol], None]]
    ],
    dry_run: bool,
    timeout_s: float | None,
    extra_switches: tuple[str, ...],
    ascii_raw: bool,
    should_cancel: Callable[[], bool] | None,
    cancel_warning: str,
    record_run: Callable[[SimulationBatchRun], None],
    warnings: list[str],
) -> None:
    total_runs = len(pending_run_defs)
    for step_index, (index, label, assignment, edit_kind, apply_edit) in enumerate(
        pending_run_defs,
        start=1,
    ):
        if should_cancel is not None and should_cancel():
            warnings.append(cancel_warning)
            break
        record_run(
            execute_sweep_run(
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
            )
        )
        report_progress(
            step_index,
            total=total_runs,
            message=f"sweep run {step_index}/{total_runs}: {label}",
        )


def _execute_pending_runs_in_parallel(
    *,
    source_path: Path,
    workspace_root: Path,
    settings: QSpiceSettings | None,
    output_root: Path,
    pending_run_defs: Sequence[
        tuple[int, str, Mapping[str, object], SweepKind, Callable[[_QschEditorProtocol], None]]
    ],
    max_workers: int,
    dry_run: bool,
    timeout_s: float | None,
    extra_switches: tuple[str, ...],
    ascii_raw: bool,
    should_cancel: Callable[[], bool] | None,
    record_run: Callable[[SimulationBatchRun], None],
    warnings: list[str],
) -> None:
    total_runs = len(pending_run_defs)
    completed_lock = threading.Lock()
    completed_count = 0

    def record_run_with_progress(run: SimulationBatchRun) -> None:
        nonlocal completed_count
        record_run(run)
        with completed_lock:
            completed_count += 1
            step_index = completed_count
        report_progress(
            step_index,
            total=total_runs,
            message=f"sweep run {step_index}/{total_runs}: {run.label}",
        )

    _, parallel_warnings = execute_sweep_runs_in_parallel(
        source_path=source_path,
        workspace_root=workspace_root,
        settings=settings,
        output_root=output_root,
        run_defs=pending_run_defs,
        max_workers=max_workers,
        dry_run=dry_run,
        timeout_s=timeout_s,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        should_cancel=should_cancel,
        on_run_complete=record_run_with_progress,
    )
    warnings.extend(parallel_warnings)


def run_resumable_sweep_batch(
    *,
    source_path: Path,
    workspace_root: Path,
    settings: QSpiceSettings | None,
    output_root: Path,
    sweep_kind: SweepKind,
    planned_runs: Sequence[
        tuple[int, str, Mapping[str, object], Callable[[_QschEditorProtocol], None]]
    ],
    parallelism: int,
    dry_run: bool,
    timeout_s: float | None,
    extra_switches: tuple[str, ...],
    ascii_raw: bool,
    warnings: Sequence[str] = (),
    reference: str | None = None,
    parameter_names: Sequence[str] = (),
    resume: bool = False,
    retained_artifact_policy: RetainedArtifactPolicy = "cleanup",
    batch_id: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_run_complete: Callable[[SimulationBatchRun], None] | None = None,
    submitted_at: datetime | None = None,
    plan_path: Path | None = None,
    seed: int | None = None,
    cancel_warning: str = "Batch execution was canceled before all requested runs started.",
) -> SimulationBatch:
    """Execute one sweep-like batch with optional manifest-based resume support."""

    active_retained_artifact_policy = _normalize_retained_artifact_policy(retained_artifact_policy)
    active_submitted_at = submitted_at or datetime.now().astimezone()
    expected_runs = tuple(
        (index, label, assignment) for index, label, assignment, _ in planned_runs
    )
    resumed = (
        load_resumable_batch_state(
            output_root=output_root,
            workspace_root=workspace_root,
            source_path=source_path,
            sweep_kind=sweep_kind,
            expected_runs=expected_runs,
            reference=reference,
            parameter_names=parameter_names,
            plan_path=plan_path,
            seed=seed,
        )
        if resume
        else ResumableBatchState()
    )
    if resumed.submitted_at is not None:
        active_submitted_at = resumed.submitted_at

    active_warnings = list(warnings)
    active_warnings.extend(resumed.warnings)
    resolved_batch_id = batch_id or resumed.batch_id
    sequential = not (parallelism > 1 and len(planned_runs) > 1)
    runs_by_index = {run.index: run for run in resumed.resumed_runs}
    pending_run_defs = [
        (index, label, assignment, sweep_kind, apply_edit)
        for index, label, assignment, apply_edit in planned_runs
        if index not in resumed.completed_indexes
    ]
    active_warnings.extend(
        _prepare_retained_artifacts(
            output_root=output_root,
            source_path=source_path,
            planned_runs=planned_runs,
            completed_indexes=resumed.completed_indexes,
            resume=resume,
            had_manifest=resumed.had_manifest,
            retained_artifact_policy=active_retained_artifact_policy,
        )
    )

    def _persist(status: BatchState, *, completed_at: datetime | None = None) -> None:
        save_batch_manifest(
            _build_batch_snapshot(
                source_path=source_path,
                output_root=output_root,
                sweep_kind=sweep_kind,
                run_count=len(planned_runs),
                parallelism=parallelism,
                sequential=sequential,
                runs=tuple(runs_by_index.values()),
                warnings=tuple(active_warnings),
                batch_id=resolved_batch_id,
                status=status,
                submitted_at=active_submitted_at,
                completed_at=completed_at,
                reference=reference,
                parameter_names=tuple(parameter_names),
                plan_path=plan_path,
                seed=seed,
            )
        )

    def _record_run(run: SimulationBatchRun) -> None:
        if run.index in runs_by_index:
            return
        runs_by_index[run.index] = run
        _persist("running")
        if on_run_complete is not None:
            on_run_complete(run)

    if pending_run_defs:
        _persist("running")
        if sequential:
            _execute_pending_runs_sequentially(
                source_path=source_path,
                workspace_root=workspace_root,
                settings=settings,
                output_root=output_root,
                pending_run_defs=pending_run_defs,
                dry_run=dry_run,
                timeout_s=timeout_s,
                extra_switches=extra_switches,
                ascii_raw=ascii_raw,
                should_cancel=should_cancel,
                cancel_warning=cancel_warning,
                record_run=_record_run,
                warnings=active_warnings,
            )
        else:
            _execute_pending_runs_in_parallel(
                source_path=source_path,
                workspace_root=workspace_root,
                settings=settings,
                output_root=output_root,
                pending_run_defs=pending_run_defs,
                max_workers=parallelism,
                dry_run=dry_run,
                timeout_s=timeout_s,
                extra_switches=extra_switches,
                ascii_raw=ascii_raw,
                should_cancel=should_cancel,
                record_run=_record_run,
                warnings=active_warnings,
            )

    completed_at = datetime.now().astimezone()
    final_status: BatchState = (
        "completed" if len(runs_by_index) == len(planned_runs) else "canceled"
    )
    return save_batch_manifest(
        _build_batch_snapshot(
            source_path=source_path,
            output_root=output_root,
            sweep_kind=sweep_kind,
            run_count=len(planned_runs),
            parallelism=parallelism,
            sequential=sequential,
            runs=tuple(runs_by_index.values()),
            warnings=tuple(active_warnings),
            batch_id=resolved_batch_id,
            status=final_status,
            submitted_at=active_submitted_at,
            completed_at=completed_at,
            reference=reference,
            parameter_names=tuple(parameter_names),
            plan_path=plan_path,
            seed=seed,
        )
    )


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
) -> SimulationBatchRun:
    """Create one edited schematic variant, then generate and run it."""

    return _execute_sweep_run_impl(
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
        open_editor=open_schematic_editor,
        save_schematic=save_edited_schematic,
        generate_netlist_fn=generate_netlist,
        run_simulation_fn=run_simulation,
        save_run_record=save_batch_run_record,
    )


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
    should_cancel: Callable[[], bool] | None = None,
    on_run_complete: Callable[[SimulationBatchRun], None] | None = None,
) -> tuple[list[SimulationBatchRun], list[str]]:
    """Execute independent sweep runs in parallel using a thread pool."""

    return _execute_sweep_runs_in_parallel_impl(
        source_path=source_path,
        workspace_root=workspace_root,
        settings=settings,
        output_root=output_root,
        run_defs=run_defs,
        max_workers=max_workers,
        dry_run=dry_run,
        timeout_s=timeout_s,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        open_editor=open_schematic_editor,
        save_schematic=save_edited_schematic,
        generate_netlist_fn=generate_netlist,
        run_simulation_fn=run_simulation,
        save_run_record=save_batch_run_record,
        should_cancel=should_cancel,
        on_run_complete=on_run_complete,
    )


__all__ = [
    "BatchState",
    "ResumableBatchState",
    "RetainedArtifactPolicy",
    "SimulationBatch",
    "SimulationBatchRun",
    "SweepKind",
    "batch_manifest_path",
    "batch_run_record_path",
    "build_run_paths",
    "execute_sweep_run",
    "execute_sweep_runs_in_parallel",
    "load_batch_manifest",
    "load_batch_run_record",
    "load_resumable_batch_state",
    "resolve_sweep_output_root",
    "run_resumable_sweep_batch",
    "save_batch_manifest",
    "save_batch_run_record",
    "slugify",
    "validate_sweep_source",
]
