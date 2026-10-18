# In the name of God, the Most Gracious, the Most Merciful
"""Per-call workspace root, isolated from shared server settings."""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

_pending_workspace_root: ContextVar[Path | None] = ContextVar(
    "pending_workspace_root",
    default=None,
)


def set_pending_workspace_root(workspace_root: Path | None) -> Token[Path | None]:
    """Stash one workspace-root override for the active call."""

    return _pending_workspace_root.set(workspace_root)


def get_pending_workspace_root() -> Path | None:
    """Return the workspace-root override stashed for the active call."""

    return _pending_workspace_root.get()


def reset_pending_workspace_root(token: Token[Path | None]) -> None:
    """Clear one stashed workspace-root override."""

    _pending_workspace_root.reset(token)


def settings_for_active_workspace(settings: QSpiceSettings) -> QSpiceSettings:
    """Return settings whose workspace root matches the active call, if any.

    The returned object is a copy when an override is present, so concurrent
    calls cannot clobber a shared settings instance.
    """

    pending = get_pending_workspace_root()
    if pending is None:
        return settings
    resolved = pending.resolve(strict=False)
    if resolved == settings.workspace_root:
        return settings
    return settings.model_copy(update={"workspace_root": resolved})


__all__ = [
    "get_pending_workspace_root",
    "reset_pending_workspace_root",
    "set_pending_workspace_root",
    "settings_for_active_workspace",
]
