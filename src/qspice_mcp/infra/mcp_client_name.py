# In the name of God, the Most Gracious, the Most Merciful
"""MCP client name captured from initialize and shown while a live GUI session is open."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from mcp.server.session import ServerSession

if TYPE_CHECKING:
    from typing import Any


class _ClientNameState:
    initialized: str | None = None
    visible: str | None = None
    hook_installed: bool = False


_LOCK = threading.Lock()
_STATE = _ClientNameState()


def record_mcp_client_name(name: str) -> None:
    """Store the client name from an MCP initialize request."""

    cleaned = name.strip()
    if not cleaned:
        return
    with _LOCK:
        _STATE.initialized = cleaned


def show_mcp_client_name() -> str | None:
    """Make the initialized client name visible for an open live GUI session."""

    with _LOCK:
        _STATE.visible = _STATE.initialized
        return _STATE.visible


def current_mcp_client_name() -> str | None:
    """Return the client name while a live GUI session is showing it."""

    with _LOCK:
        return _STATE.visible


def clear_mcp_client_name() -> None:
    """Stop showing the client name after the last live GUI session closes."""

    with _LOCK:
        _STATE.visible = None


def _capture_initialize_request(responder: object) -> None:
    request = getattr(responder, "request", None)
    root = getattr(request, "root", None)
    if getattr(root, "method", None) != "initialize":
        return
    params = getattr(root, "params", None)
    client_info = getattr(params, "clientInfo", None)
    name = getattr(client_info, "name", None)
    if isinstance(name, str):
        record_mcp_client_name(name)


def install_initialize_client_hook() -> None:
    """Record ``clientInfo.name`` when the MCP session handles initialize."""

    if _STATE.hook_installed:
        return
    _STATE.hook_installed = True
    original = ServerSession._received_request

    async def _received_request(self: ServerSession, responder: Any) -> None:
        _capture_initialize_request(responder)
        await original(self, responder)

    ServerSession._received_request = _received_request  # type: ignore[method-assign]


def record_client_name_from_session(session: object | None) -> None:
    """Record a client name already stored on an initialized MCP session."""

    params = getattr(session, "client_params", None)
    client_info = getattr(params, "clientInfo", None)
    name = getattr(client_info, "name", None)
    if isinstance(name, str):
        record_mcp_client_name(name)


__all__ = [
    "clear_mcp_client_name",
    "current_mcp_client_name",
    "install_initialize_client_hook",
    "record_client_name_from_session",
    "record_mcp_client_name",
    "show_mcp_client_name",
]
