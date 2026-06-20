"""Mirror structlog events to the active MCP client when a request context is bound."""

from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING, Any

import anyio

if TYPE_CHECKING:
    from collections.abc import MutableMapping
    from contextvars import Token

_MCP_CLIENT_LOG_CONTEXT: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "qspice_mcp_client_log_context",
    default=None,
)

_LEVEL_METHODS = {
    "debug": "debug",
    "info": "info",
    "warning": "warning",
    "warn": "warning",
    "error": "error",
    "critical": "error",
}


def bind_mcp_client_log_context(context: Any | None) -> Token[Any | None]:
    """Bind one FastMCP request context for client log mirroring."""

    return _MCP_CLIENT_LOG_CONTEXT.set(context)


def reset_mcp_client_log_context(token: Token[Any | None]) -> None:
    """Reset the client log bridge after a tool call completes."""

    _MCP_CLIENT_LOG_CONTEXT.reset(token)


async def _emit_async(context: Any, method_name: str, message: str) -> None:
    method = getattr(context, method_name, None)
    if method is None:
        return
    result = method(message)
    if hasattr(result, "__await__"):
        await result


def mirror_client_log(level: str, message: str) -> None:
    """Mirror one log line to the MCP client when a context is bound."""

    context = _MCP_CLIENT_LOG_CONTEXT.get()
    if context is None or not message:
        return
    method_name = _LEVEL_METHODS.get(level.lower(), "info")
    try:
        anyio.from_thread.run(_emit_async, context, method_name, message)
    except RuntimeError:
        return


def mcp_client_log_processor(
    _logger: object,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor that forwards tool lifecycle events to MCP clients."""

    event = event_dict.get("event")
    if not isinstance(event, str):
        return event_dict
    if event not in {
        "tool_request_started",
        "tool_request_completed",
        "tool_request_failed",
    }:
        return event_dict
    level = str(event_dict.get("level", method_name))
    tool_name = event_dict.get("tool")
    duration = event_dict.get("duration_s")
    parts = [event.replace("_", " ")]
    if isinstance(tool_name, str):
        parts.append(f"tool={tool_name}")
    if isinstance(duration, (int, float)):
        parts.append(f"duration_s={duration:.3f}")
    mirror_client_log(level, "; ".join(parts))
    return event_dict


__all__ = [
    "bind_mcp_client_log_context",
    "mcp_client_log_processor",
    "mirror_client_log",
    "reset_mcp_client_log_context",
]
