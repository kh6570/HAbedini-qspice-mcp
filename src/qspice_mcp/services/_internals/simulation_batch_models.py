"""Shared models and type aliases for simulation batch helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

SweepKind = Literal["component_value", "parameter", "model", "monte_carlo", "worst_case"]
BatchState = Literal[
    "queued",
    "running",
    "completed",
    "failed",
    "canceled",
    "cancel_requested",
]
RetainedArtifactPolicy = Literal["cleanup", "keep_orphans", "keep_stale", "keep_all"]

_RETAINED_ARTIFACT_POLICIES = frozenset({"cleanup", "keep_orphans", "keep_stale", "keep_all"})


@dataclass(frozen=True, slots=True)
class SimulationBatchRun:
    """One realized or planned run inside a sweep batch."""

    index: int
    label: str
    assignment: dict[str, object]
    schematic_path: Path
    netlist_path: Path
    log_path: Path
    raw_path: Path
    command: tuple[str, ...]
    dry_run: bool
    exit_code: int | None = None
    duration_s: float | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SimulationBatch:
    """Metadata and results for one synchronous sweep batch."""

    source_path: Path
    output_root: Path
    sweep_kind: SweepKind
    run_count: int
    parallelism: int
    sequential: bool
    runs: tuple[SimulationBatchRun, ...]
    reference: str | None = None
    parameter_names: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    batch_id: str | None = None
    status: BatchState = "completed"
    completed_run_count: int | None = None
    manifest_path: Path | None = None
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    plan_path: Path | None = None
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class ResumableBatchState:
    """Existing successful runs that can be reused for one rerun request."""

    resumed_runs: tuple[SimulationBatchRun, ...] = ()
    completed_indexes: frozenset[int] = frozenset()
    warnings: tuple[str, ...] = ()
    submitted_at: datetime | None = None
    batch_id: str | None = None
    had_manifest: bool = False


__all__ = [
    "BatchState",
    "ResumableBatchState",
    "RetainedArtifactPolicy",
    "SimulationBatch",
    "SimulationBatchRun",
    "SweepKind",
]
