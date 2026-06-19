"""MCP progress notification bridge for sync tool bodies running off-thread."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import anyio

if TYPE_CHECKING:
    from collections.abc import Iterator

_PROGRESS_CONTEXT: contextvars.ContextVar[ProgressBridge | None] = contextvars.ContextVar(
    "qspice_mcp_progress_bridge",
    default=None,
)


@dataclass(slots=True)
class ProgressBridge:
    """Emit MCP progress notifications from worker threads."""

    context: Any | None

    async def _report_async(
        self,
        progress: float,
        total: float | None,
        message: str | None,
    ) -> None:
        if self.context is None:
            return
        await self.context.report_progress(progress, total=total, message=message)

    def report(
        self,
        progress: float,
        *,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        """Report progress, safe to call from a worker thread."""

        if self.context is None:
            return
        try:
            anyio.from_thread.run(self._report_async, progress, total, message)
        except RuntimeError:
            return


@contextmanager
def progress_scope(context: Any | None) -> Iterator[None]:
    """Bind one MCP request context for progress reporting."""

    token = _PROGRESS_CONTEXT.set(ProgressBridge(context))
    try:
        yield
    finally:
        _PROGRESS_CONTEXT.reset(token)


def get_progress_bridge() -> ProgressBridge | None:
    """Return the active progress bridge for the current request, if any."""

    return _PROGRESS_CONTEXT.get()


def report_progress(
    progress: float,
    *,
    total: float | None = None,
    message: str | None = None,
) -> None:
    """Report progress when a bridge is bound for the active tool call."""

    bridge = get_progress_bridge()
    if bridge is not None:
        bridge.report(progress, total=total, message=message)


def bind_context(context: Any) -> contextvars.Token[ProgressBridge | None]:
    """Bind a FastMCP context for progress reporting (used by the server)."""

    return _PROGRESS_CONTEXT.set(ProgressBridge(context))


def reset_context(token: contextvars.Token[ProgressBridge | None]) -> None:
    """Reset the progress bridge after a tool call completes."""

    _PROGRESS_CONTEXT.reset(token)


__all__ = [
    "ProgressBridge",
    "bind_context",
    "get_progress_bridge",
    "progress_scope",
    "report_progress",
    "reset_context",
]
