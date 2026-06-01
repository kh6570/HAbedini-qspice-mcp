"""Service for sweeping one component model across multiple runs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import (
    resolve_sweep_output_root,
    run_resumable_sweep_batch,
    validate_sweep_source,
)
from qspice_mcp.services.service_spec import ServiceSpec

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

SERVICE_SPEC = ServiceSpec(
    name="run_model_sweep",
    title="Run Model Sweep",
    summary="Run one schematic across multiple element models.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


def _make_model_apply_edit(reference: str, model: str) -> Callable[[_QschEditorProtocol], None]:
    def _apply(editor: _QschEditorProtocol) -> None:
        editor.set_element_model(reference, model)

    return _apply


def run_model_sweep(
    source_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    models: tuple[str, ...] | list[str],
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
    """Run a synchronous sweep that changes one element model per run."""

    if parallelism < 1:
        raise ValueError("parallelism must be at least 1")
    if not models:
        raise ValueError("models must contain at least one entry")

    workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_sweep_source(source_path, workspace_root=workspace)
    resolved_output = resolve_sweep_output_root(
        output_dir,
        workspace_root=workspace,
        source_path=resolved_source,
        sweep_kind="model",
    )

    requested_models = tuple(models)
    planned_runs = tuple(
        (
            index,
            f"{reference}={model}",
            {reference: model},
            _make_model_apply_edit(reference, model),
        )
        for index, model in enumerate(requested_models)
    )
    return run_resumable_sweep_batch(
        source_path=resolved_source,
        workspace_root=workspace,
        settings=settings,
        output_root=resolved_output,
        sweep_kind="model",
        planned_runs=planned_runs,
        parallelism=parallelism,
        dry_run=dry_run,
        timeout_s=timeout_s,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        reference=reference,
        resume=resume,
        retained_artifact_policy=retained_artifact_policy,
        batch_id=batch_id,
        should_cancel=should_cancel,
        on_run_complete=on_run_complete,
        submitted_at=datetime.now().astimezone(),
    )


__all__ = ["SERVICE_SPEC", "run_model_sweep"]
