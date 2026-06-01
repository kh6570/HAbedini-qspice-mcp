"""Service metadata for batch cancellation requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._internals.simulation_batch import BatchState, SweepKind


@dataclass(frozen=True, slots=True)
class BatchCancellation:
    """Acknowledgement for one batch cancellation request."""

    batch_id: str
    batch_kind: SweepKind
    status: BatchState
    output_root: Path
    cancellation_requested: bool
    note: str


SERVICE_SPEC = ServiceSpec(
    name="cancel_batch",
    title="Cancel Batch",
    summary="Request cancellation for one submitted batch.",
    phase="implemented",
    read_only=False,
)


__all__ = ["SERVICE_SPEC", "BatchCancellation"]
