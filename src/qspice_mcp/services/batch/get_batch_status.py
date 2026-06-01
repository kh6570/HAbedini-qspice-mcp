"""Service metadata for background batch status reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from qspice_mcp.services._internals.simulation_batch import BatchState, SweepKind


@dataclass(frozen=True, slots=True)
class BatchStatus:
    """Live or final status for one submitted batch."""

    batch_id: str
    batch_kind: SweepKind
    status: BatchState
    source_path: Path
    output_root: Path
    manifest_path: Path
    run_count: int | None = None
    completed_run_count: int = 0
    cancellation_requested: bool = False
    submitted_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


SERVICE_SPEC = ServiceSpec(
    name="get_batch_status",
    title="Get Batch Status",
    summary="Read the live status of one submitted batch.",
    phase="implemented",
)


__all__ = ["SERVICE_SPEC", "BatchStatus"]
