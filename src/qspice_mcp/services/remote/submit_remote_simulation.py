"""Service metadata for background remote-style simulation submission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

RemoteSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class RemoteSimulationSubmission:
    """Metadata returned when one remote-style simulation session is accepted."""

    session_id: str
    status: RemoteSessionState
    source_path: Path
    output_root: Path
    submitted_at: datetime
    owner_host_id: str


SERVICE_SPEC = ServiceSpec(
    name="submit_remote_simulation",
    title="Submit Remote Simulation",
    summary="Submit one remote-style simulation session for background execution and transport.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


__all__ = ["SERVICE_SPEC", "RemoteSimulationSubmission"]
