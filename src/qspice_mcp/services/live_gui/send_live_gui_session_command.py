"""Service metadata for queueing one live GUI bridge command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class LiveGuiSessionCommandDispatch:
    """Metadata returned after one live GUI bridge command is queued."""

    session_id: str
    command_id: int
    command: str
    signal: str | None
    payload: dict[str, object]
    queued_at: datetime
    command_path: Path
    note: str


SERVICE_SPEC = ServiceSpec(
    name="send_live_gui_session_command",
    title="Send Live GUI Session Command",
    summary=(
        "Queue one command for the external live GUI bridge to translate into Windows messages."
    ),
    phase="implemented",
    read_only=False,
)


__all__ = ["SERVICE_SPEC", "LiveGuiSessionCommandDispatch"]
