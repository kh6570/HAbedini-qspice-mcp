"""Service for running a prepared Monte Carlo parameter plan."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import (
    run_resumable_sweep_batch,
    validate_sweep_source,
)
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._statistical_helpers import (
    apply_assignment,
    build_assignment_payload,
)
from qspice_mcp.services.simulation.prepare_monte_carlo import load_prepared_monte_carlo

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol
    from qspice_mcp.services._internals.simulation_batch import (
        RetainedArtifactPolicy,
        SimulationBatch,
        SimulationBatchRun,
    )
    from qspice_mcp.services.simulation.prepare_monte_carlo import MonteCarloSample


SERVICE_SPEC = ServiceSpec(
    name="run_monte_carlo",
    title="Run Monte Carlo",
    summary="Run one prepared Monte Carlo parameter plan as a copy-on-write batch.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


def _make_sample_apply_edit(sample: MonteCarloSample) -> Callable[[_QschEditorProtocol], None]:
    def _apply(editor: _QschEditorProtocol) -> None:
        apply_assignment(
            editor,
            parameter_values=sample.parameter_values,
            component_values=sample.component_values,
        )

    return _apply


def run_monte_carlo(
    prepared_path: str | Path,
    *,
    workspace_root: Path,
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
    """Execute one prepared Monte Carlo plan through the schematic batch runner."""

    if parallelism < 1:
        raise ValueError("parallelism must be at least 1")

    workspace = workspace_root.resolve(strict=False)
    prepared = load_prepared_monte_carlo(prepared_path, workspace_root=workspace)
    resolved_source = validate_sweep_source(prepared.source_path, workspace_root=workspace)
    resolved_output = (
        resolve_workspace_path(output_dir, workspace_root=workspace)
        if output_dir is not None
        else prepared.output_root
    )

    planned_runs = tuple(
        (
            sample.index,
            sample.label or f"sample-{sample.index:03d}",
            build_assignment_payload(
                parameter_values=sample.parameter_values,
                component_values=sample.component_values,
            ),
            _make_sample_apply_edit(sample),
        )
        for sample in prepared.samples
    )
    return run_resumable_sweep_batch(
        source_path=resolved_source,
        workspace_root=workspace,
        settings=settings,
        output_root=resolved_output,
        sweep_kind="monte_carlo",
        planned_runs=planned_runs,
        parallelism=parallelism,
        dry_run=dry_run,
        timeout_s=timeout_s,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        warnings=prepared.warnings,
        parameter_names=tuple(parameter.name for parameter in prepared.parameters),
        resume=resume,
        retained_artifact_policy=retained_artifact_policy,
        batch_id=batch_id,
        should_cancel=should_cancel,
        on_run_complete=on_run_complete,
        submitted_at=datetime.now().astimezone(),
        plan_path=prepared.plan_path,
        seed=prepared.seed,
        cancel_warning="Monte Carlo execution was canceled before all requested runs started.",
    )


__all__ = ["SERVICE_SPEC", "run_monte_carlo"]
