"""Service metadata for collecting completed batch results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.services._internals.simulation_batch import BatchState, SimulationBatch


@dataclass(frozen=True, slots=True)
class BatchCollection:
    """Collected batch results or the reason they are unavailable."""

    batch_id: str
    status: BatchState
    batch: SimulationBatch | None
    error: str | None = None


SERVICE_SPEC = ServiceSpec(
    name="collect_batch_results",
    title="Collect Batch Results",
    summary="Return the completed batch manifest and per-run results.",
    phase="implemented",
)


__all__ = ["SERVICE_SPEC", "BatchCollection"]
