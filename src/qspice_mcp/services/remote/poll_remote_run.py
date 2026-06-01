"""Service metadata for polling a remote-style simulation session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

RemoteSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class RemoteRunStatus:
    """Live or terminal status for one remote-style simulation session."""

    session_id: str
    status: RemoteSessionState
    source_path: Path
    output_root: Path
    submitted_at: datetime
    completed_at: datetime | None
    simulation_input_path: Path | None
    log_path: Path | None
    raw_path: Path | None
    bundle_path: Path | None
    dry_run: bool
    exit_code: int | None
    duration_s: float | None
    log_available: bool
    raw_available: bool
    bundle_available: bool
    owner_host_id: str | None = None
    lease_heartbeat_at: datetime | None = None
    error: str | None = None


SERVICE_SPEC = ServiceSpec(
    name="poll_remote_run",
    title="Poll Remote Run",
    summary="Read live status for one submitted remote-style simulation session.",
    phase="implemented",
)


__all__ = ["SERVICE_SPEC", "RemoteRunStatus"]
