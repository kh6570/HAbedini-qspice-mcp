"""Service for sweeping schematic parameters across multiple runs."""

from __future__ import annotations

from datetime import datetime
from itertools import product
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import (
    resolve_sweep_output_root,
    run_resumable_sweep_batch,
    validate_sweep_source,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol
    from qspice_mcp.services._internals.simulation_batch import (
        RetainedArtifactPolicy,
        SimulationBatch,
        SimulationBatchRun,
    )

SERVICE_SPEC = ServiceSpec(
    name="run_param_sweep",
    title="Run Parameter Sweep",
    summary="Run one schematic across the Cartesian product of parameter values.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


def _make_combo_apply_edit(
    parameter_names: tuple[str, ...],
    combo: tuple[str | int | float | bool, ...],
) -> Callable[[_QschEditorProtocol], None]:
    def _apply(editor: _QschEditorProtocol) -> None:
        for name, value in zip(parameter_names, combo, strict=True):
            editor.set_parameter(name, value)

    return _apply


def run_param_sweep(
    source_path: str | Path,
    *,
    workspace_root: Path,
    parameters: Mapping[str, Sequence[str | int | float | bool]],
    settings: QSpiceSettings | None = None,
    output_dir: str | Path | None = None,
    parallelism: int = 1,
    dry_run: bool = False,
    timeout_s: float | None = None,
    ascii_raw: bool = False,
    extra_switches: tuple[str, ...] = (),
    resume: bool = False,
    retained_artifact_policy: RetainedArtifactPolicy = "cleanup",
    batch_id: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_run_complete: Callable[[SimulationBatchRun], None] | None = None,
) -> SimulationBatch:
    """Run a synchronous sweep across parameter combinations."""

    if parallelism < 1:
        raise ValueError("parallelism must be at least 1")
    if not parameters:
        raise ValueError("parameters must contain at least one named parameter")

    parameter_names = tuple(parameters)
    parameter_values = tuple(tuple(parameters[name]) for name in parameter_names)
    if any(not values for values in parameter_values):
        raise ValueError("each parameter must contain at least one candidate value")

    workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_sweep_source(source_path, workspace_root=workspace)
    resolved_output = resolve_sweep_output_root(
        output_dir,
        workspace_root=workspace,
        source_path=resolved_source,
        sweep_kind="parameter",
    )

    combinations = tuple(product(*parameter_values))
    planned_runs = tuple(
        (
            index,
            "_".join(f"{name}={value}" for name, value in zip(parameter_names, combo, strict=True)),
            dict(zip(parameter_names, combo, strict=True)),
            _make_combo_apply_edit(parameter_names, combo),
        )
        for index, combo in enumerate(combinations)
    )
    return run_resumable_sweep_batch(
        source_path=resolved_source,
        workspace_root=workspace,
        settings=settings,
        output_root=resolved_output,
        sweep_kind="parameter",
        planned_runs=planned_runs,
        parallelism=parallelism,
        dry_run=dry_run,
        timeout_s=timeout_s,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        parameter_names=parameter_names,
        resume=resume,
        retained_artifact_policy=retained_artifact_policy,
        batch_id=batch_id,
        should_cancel=should_cancel,
        on_run_complete=on_run_complete,
        submitted_at=datetime.now().astimezone(),
    )


__all__ = ["SERVICE_SPEC", "run_param_sweep"]
