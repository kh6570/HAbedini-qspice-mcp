"""Service metadata for polling a live GUI bridge session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

LiveGuiSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class LiveGuiSessionStatus:
    """Status returned when polling one live GUI bridge session."""

    session_id: str
    session_name: str
    status: LiveGuiSessionState
    manifest_path: Path
    output_root: Path
    bridge_command: tuple[str, ...]
    submitted_at: datetime
    completed_at: datetime | None
    bridge_pid: int | None
    bridge_exit_code: int | None
    duration_s: float | None
    live_process_attached: bool
    stdout_path: Path
    stderr_path: Path
    error: str | None = None
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="poll_live_gui_session",
    title="Poll Live GUI Session",
    summary="Read live or terminal status for one launched live GUI bridge session.",
    phase="implemented",
)


__all__ = ["SERVICE_SPEC", "LiveGuiSessionStatus"]
