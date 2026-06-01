"""Service metadata for background batch submission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from qspice_mcp.services._internals.simulation_batch import BatchState, SweepKind


@dataclass(frozen=True, slots=True)
class BatchSubmission:
    """Metadata returned when a batch is accepted for execution."""

    batch_id: str
    batch_kind: SweepKind
    status: BatchState
    source_path: Path
    output_root: Path
    manifest_path: Path
    submitted_at: datetime


SERVICE_SPEC = ServiceSpec(
    name="submit_batch",
    title="Submit Batch",
    summary="Submit a sweep batch for background execution.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


__all__ = ["SERVICE_SPEC", "BatchSubmission"]
