"""Service for summarizing persisted batch artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import (
    BatchState,
    SweepKind,
    load_batch_manifest,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class BatchRunSummary:
    """Artifact and status metadata for one batch run."""

    index: int
    label: str
    assignment: dict[str, object]
    schematic_path: Path
    netlist_path: Path
    log_path: Path
    raw_path: Path
    exit_code: int | None
    duration_s: float | None
    dry_run: bool
    log_available: bool
    raw_available: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BatchSummary:
    """A concise persisted summary of one simulation batch."""

    manifest_path: Path
    batch_id: str | None
    source_path: Path
    output_root: Path
    sweep_kind: SweepKind
    status: BatchState
    run_count: int
    completed_run_count: int
    successful_run_count: int
    failed_run_count: int
    runs: tuple[BatchRunSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="summarize_batch",
    title="Summarize Batch",
    summary="Summarize one persisted batch manifest and its derived artifacts.",
    phase="implemented",
)


def summarize_batch(
    batch_path: str | Path,
    *,
    workspace_root: Path,
) -> BatchSummary:
    """Summarize one saved batch manifest and its run artifacts."""

    batch = load_batch_manifest(batch_path, workspace_root=workspace_root.resolve(strict=False))
    warnings = list(batch.warnings)
    runs: list[BatchRunSummary] = []
    successful_run_count = 0
    failed_run_count = 0

    for run in batch.runs:
        log_available = run.log_path.is_file()
        raw_available = run.raw_path.is_file()
        if run.exit_code == 0:
            successful_run_count += 1
            if not run.dry_run and not log_available:
                warnings.append(f"Run {run.index} ({run.label}) is missing its .log artifact.")
            if not run.dry_run and not raw_available:
                warnings.append(f"Run {run.index} ({run.label}) is missing its .qraw artifact.")
        elif run.exit_code is not None:
            failed_run_count += 1

        runs.append(
            BatchRunSummary(
                index=run.index,
                label=run.label,
                assignment=dict(run.assignment),
                schematic_path=run.schematic_path,
                netlist_path=run.netlist_path,
                log_path=run.log_path,
                raw_path=run.raw_path,
                exit_code=run.exit_code,
                duration_s=run.duration_s,
                dry_run=run.dry_run,
                log_available=log_available,
                raw_available=raw_available,
                warnings=run.warnings,
            )
        )

    completed_run_count = batch.completed_run_count
    if completed_run_count is None:
        completed_run_count = sum(
            1 for run in batch.runs if run.exit_code is not None or run.dry_run
        )

    manifest_path = batch.manifest_path or (batch.output_root / "batch.json").resolve(strict=False)
    return BatchSummary(
        manifest_path=manifest_path,
        batch_id=batch.batch_id,
        source_path=batch.source_path,
        output_root=batch.output_root,
        sweep_kind=batch.sweep_kind,
        status=batch.status,
        run_count=batch.run_count,
        completed_run_count=completed_run_count,
        successful_run_count=successful_run_count,
        failed_run_count=failed_run_count,
        runs=tuple(runs),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = ["SERVICE_SPEC", "BatchRunSummary", "BatchSummary", "summarize_batch"]
