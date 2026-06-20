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

_STRUCTURED_LOG_FIELDS = (
    "event",
    "tool",
    "component",
    "duration_s",
    "read_only",
    "long_running",
    "trace_id",
    "error",
)


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


def _format_client_log_message(event_dict: MutableMapping[str, Any]) -> str:
    event = event_dict.get("event")
    if not isinstance(event, str):
        return ""
    parts = [event.replace("_", " ")]
    for key in _STRUCTURED_LOG_FIELDS:
        if key == "event":
            continue
        value = event_dict.get(key)
        if value is None:
            continue
        if isinstance(value, float):
            parts.append(f"{key}={value:.3f}")
        else:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


def _should_mirror_event(level: str, event_dict: MutableMapping[str, Any]) -> bool:
    if _MCP_CLIENT_LOG_CONTEXT.get() is None:
        return False
    if level in {"warning", "warn", "error", "critical"}:
        return True
    if level == "debug":
        return event_dict.get("component") == "mcp.tool"
    return True


def mcp_client_log_processor(
    _logger: object,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Structlog processor that forwards structured log events to MCP clients."""

    level = str(event_dict.get("level", method_name)).lower()
    if not _should_mirror_event(level, event_dict):
        return event_dict
    message = _format_client_log_message(event_dict)
    if message:
        mirror_client_log(level, message)
    return event_dict


__all__ = [
    "bind_mcp_client_log_context",
    "mcp_client_log_processor",
    "mirror_client_log",
    "reset_mcp_client_log_context",
]
