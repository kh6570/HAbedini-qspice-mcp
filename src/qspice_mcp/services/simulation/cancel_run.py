"""Service for cancelling an in-flight QSpice simulation run."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra.child_processes import request_run_cancellation
from qspice_mcp.services.service_spec import ServiceSpec


@dataclass(frozen=True, slots=True)
class RunCancellation:
    """Acknowledgement for one simulation run cancellation request."""

    run_id: str
    cancelled: bool


SERVICE_SPEC = ServiceSpec(
    name="cancel_run",
    title="Cancel Run",
    summary="Request cancellation of an in-flight run_simulation invocation by its run_id.",
    phase="implemented",
    read_only=False,
)


def cancel_run(run_id: str) -> RunCancellation:
    """Terminate the live process associated with ``run_id`` when one is tracked."""

    normalized = run_id.strip()
    if not normalized:
        raise ValidationError("run_id must be a non-empty string.")
    found = request_run_cancellation(normalized)
    if not found:
        raise ValidationError(f"No active simulation run is tracked for run_id {normalized!r}.")
    return RunCancellation(run_id=normalized, cancelled=True)


__all__ = ["SERVICE_SPEC", "RunCancellation", "cancel_run"]
