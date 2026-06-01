"""Workspace-root override helpers for MCP tool handlers."""

from __future__ import annotations

from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings

_pending_workspace_root: ContextVar[Path | None] = ContextVar(
    "pending_workspace_root",
    default=None,
)


class _WorkspaceSettingsProxy:
    """Expose a per-request workspace root while delegating other settings."""

    __slots__ = ("_settings", "_workspace_root")

    def __init__(self, settings: QSpiceSettings, workspace_root: Path) -> None:
        self._settings = settings
        self._workspace_root = workspace_root

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def __getattr__(self, name: str) -> Any:
        return getattr(self._settings, name)


def resolve_workspace_override(raw_workspace_root: object | None) -> Path | None:
    """Normalize one optional workspace-root override from MCP tool arguments."""

    if raw_workspace_root is None:
        return None
    text = str(raw_workspace_root).strip()
    if not text:
        return None
    return Path(text).expanduser().resolve(strict=False)


def set_pending_workspace_root(workspace_root: Path | None) -> Token[Path | None]:
    """Stash one workspace-root override for the active MCP tool call."""

    return _pending_workspace_root.set(workspace_root)


def get_pending_workspace_root() -> Path | None:
    """Return the workspace-root override stashed for the active MCP tool call."""

    return _pending_workspace_root.get()


def reset_pending_workspace_root(token: Token[Path | None]) -> None:
    """Clear one stashed workspace-root override."""

    _pending_workspace_root.reset(token)


__all__ = [
    "_WorkspaceSettingsProxy",
    "get_pending_workspace_root",
    "reset_pending_workspace_root",
    "resolve_workspace_override",
    "set_pending_workspace_root",
]
