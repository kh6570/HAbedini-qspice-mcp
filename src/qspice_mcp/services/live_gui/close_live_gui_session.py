"""Service metadata for closing a live GUI bridge session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

LiveGuiSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class LiveGuiSessionClosure:
    """Metadata returned when one live GUI bridge session is closed."""

    session_id: str
    status: LiveGuiSessionState
    output_root: Path
    manifest_path: Path
    bridge_terminated: bool
    manifest_deleted: bool
    note: str


SERVICE_SPEC = ServiceSpec(
    name="close_live_gui_session",
    title="Close Live GUI Session",
    summary="Close one launched live GUI bridge session and optionally delete its manifest.",
    phase="implemented",
    read_only=False,
)


__all__ = ["SERVICE_SPEC", "LiveGuiSessionClosure"]
