"""Service metadata for closing a remote-style simulation session."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

RemoteSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class RemoteSessionClosure:
    """Metadata returned when a remote-style session is closed."""

    session_id: str
    status: RemoteSessionState
    output_root: Path
    bundle_deleted: bool
    note: str


SERVICE_SPEC = ServiceSpec(
    name="close_remote_session",
    title="Close Remote Session",
    summary="Close one remote-style simulation session and optionally discard its bundle.",
    phase="implemented",
    read_only=False,
)


__all__ = ["SERVICE_SPEC", "RemoteSessionClosure"]
