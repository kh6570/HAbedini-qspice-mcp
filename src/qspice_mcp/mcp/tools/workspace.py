"""Workspace-root override helpers for MCP tool handlers."""

from __future__ import annotations

import re
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qspice_mcp.infra.config import QSpiceSettings

_pending_workspace_root: ContextVar[Path | None] = ContextVar(
    "pending_workspace_root",
    default=None,
)

_WINDOWS_DRIVE_PREFIX = re.compile(r"^/[A-Za-z]:")


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


def root_uri_to_path(uri: str) -> Path | None:
    """Convert one ``file://`` MCP root URI into a local path, else ``None``."""

    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    raw_path = unquote(parsed.path)
    if not raw_path:
        return None
    # ``file:///C:/work`` parses to ``/C:/work`` on every platform; drop the
    # spurious leading slash before the Windows drive letter.
    if _WINDOWS_DRIVE_PREFIX.match(raw_path):
        raw_path = raw_path[1:]
    return Path(raw_path)


def pick_workspace_root_from_roots(root_uris: Sequence[str]) -> Path | None:
    """Return the first advertised ``file://`` root that is an existing directory."""

    for uri in root_uris:
        candidate = root_uri_to_path(uri)
        if candidate is not None and candidate.is_dir():
            return candidate.resolve(strict=False)
    return None


def choose_effective_workspace_root(
    *,
    override: Path | None,
    configured: Path,
    process_default: Path,
    advertised_root: Path | None,
) -> Path:
    """Resolve the workspace root with explicit precedence.

    Precedence (highest first): a per-call ``workspace_root`` override, an
    explicitly configured root (CLI/env differing from the process default), the
    first advertised MCP client root, then the configured default.
    """

    if override is not None:
        return override
    if configured.resolve(strict=False) != process_default.resolve(strict=False):
        return configured
    if advertised_root is not None:
        return advertised_root
    return configured


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
    "choose_effective_workspace_root",
    "get_pending_workspace_root",
    "pick_workspace_root_from_roots",
    "reset_pending_workspace_root",
    "resolve_workspace_override",
    "root_uri_to_path",
    "set_pending_workspace_root",
]
