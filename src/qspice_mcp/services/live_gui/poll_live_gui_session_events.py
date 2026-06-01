"""Service metadata for reading live GUI bridge events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

LiveGuiSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class LiveGuiSessionEvent:
    """One persisted event produced by the external live GUI bridge."""

    sequence: int
    event: str
    created_at: datetime | None
    signal: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class LiveGuiSessionEventPoll:
    """Incremental bridge events read for one live GUI session."""

    session_id: str
    status: LiveGuiSessionState
    event_path: Path
    next_sequence: int
    events: tuple[LiveGuiSessionEvent, ...]
    live_process_attached: bool
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="poll_live_gui_session_events",
    title="Poll Live GUI Session Events",
    summary="Read bridge-produced live GUI events recorded for one launched session.",
    phase="implemented",
    read_only=True,
)


__all__ = ["SERVICE_SPEC", "LiveGuiSessionEvent", "LiveGuiSessionEventPoll"]
