"""Service metadata for launching a live GUI bridge session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

LiveGuiSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class LiveGuiSessionLaunch:
    """Metadata returned when one live GUI bridge session is launched."""

    session_id: str
    session_name: str
    status: LiveGuiSessionState
    manifest_path: Path
    output_root: Path
    bridge_command: tuple[str, ...]
    submitted_at: datetime
    bridge_pid: int | None
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="launch_live_gui_session",
    title="Launch Live GUI Session",
    summary=(
        "Launch one version-gated live GUI bridge session through a configured "
        "Windows-message bridge command."
    ),
    phase="implemented",
    read_only=False,
    long_running=True,
)


__all__ = ["SERVICE_SPEC", "LiveGuiSessionLaunch"]
