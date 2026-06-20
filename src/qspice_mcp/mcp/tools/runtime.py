"""Runtime-backed MCP tool handlers for implemented services."""

from __future__ import annotations

import asyncio
import inspect
from functools import wraps
from time import perf_counter
from typing import TYPE_CHECKING, cast

import anyio

from qspice_mcp.infra.logging import get_logger
from qspice_mcp.infra.progress import report_progress
from qspice_mcp.infra.telemetry import attach_trace_id, request_scope
from qspice_mcp.services._internals.batch_manager import SimulationBatchManager
from qspice_mcp.services._internals.live_gui_manager import LiveGuiSessionManager
from qspice_mcp.services._internals.remote_session_manager import RemoteSimulationManager

from .handler_bindings import ToolHandler, build_raw_tool_handlers
from .schema_handlers import expose_tool_schema
from .shared import to_jsonable
from .workspace import (
    _WorkspaceSettingsProxy,
    get_pending_workspace_root,
    resolve_workspace_override,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from qspice_mcp.infra.config import QSpiceSettings

    from ..tool_registry import ToolDefinition


class QSpiceToolRuntime:
    """Thin orchestration layer used by MCP tool handlers."""

    def __init__(self, settings: QSpiceSettings, tools: tuple[ToolDefinition, ...]) -> None:
        self.settings = settings.normalized()
        self.tools = tools
        self._batch_manager = SimulationBatchManager(self.settings)
        self._live_gui_manager = LiveGuiSessionManager(self.settings)
        self._remote_manager = RemoteSimulationManager(self.settings)
        self._tool_definitions = {tool.name: tool for tool in tools}
        raw_handlers = build_raw_tool_handlers(self, tools)
        self._handlers: dict[str, ToolHandler] = {
            name: self._wrap_handler(
                self._tool_definitions[name],
                expose_tool_schema(handler, self._tool_definitions[name]),
            )
            for name, handler in raw_handlers.items()
        }

    def _wrap_handler(
        self,
        tool: ToolDefinition,
        handler: Callable[..., dict[str, object]],
    ) -> ToolHandler:
        logger = get_logger(component="mcp.tool", tool=tool.name)

        def _execute(**kwargs: object) -> dict[str, object]:
            workspace_override = resolve_workspace_override(kwargs.pop("workspace_root", None))
            if workspace_override is None:
                workspace_override = get_pending_workspace_root()
            original_settings = self.settings
            if workspace_override is not None:
                self.settings = cast(
                    "QSpiceSettings",
                    _WorkspaceSettingsProxy(original_settings, workspace_override),
                )
            with request_scope(
                tool_name=tool.name,
                telemetry_enabled=self.settings.telemetry_enabled,
                long_running=tool.service.long_running,
            ) as trace_id:
                started_at = perf_counter()
                logger.info(
                    "tool_request_started",
                    read_only=tool.service.read_only,
                    long_running=tool.service.long_running,
                )
                if tool.service.long_running:
                    report_progress(0, total=1, message=f"{tool.name} started")
                try:
                    result = handler(**kwargs)
                except Exception as exc:
                    attach_trace_id(exc, trace_id)
                    logger.exception(
                        "tool_request_failed",
                        duration_s=perf_counter() - started_at,
                        long_running=tool.service.long_running,
                    )
                    raise
                finally:
                    if workspace_override is not None:
                        self.settings = original_settings

                logger.info(
                    "tool_request_completed",
                    duration_s=perf_counter() - started_at,
                    long_running=tool.service.long_running,
                )
                if tool.service.long_running:
                    report_progress(1, total=1, message=f"{tool.name} completed")
                result.setdefault("trace_id", trace_id)
                return result

        if tool.service.long_running:

            @wraps(handler)
            async def async_wrapped_handler(**kwargs: object) -> dict[str, object]:
                return await anyio.to_thread.run_sync(lambda: _execute(**kwargs))

            return cast("ToolHandler", async_wrapped_handler)

        @wraps(handler)
        def sync_wrapped_handler(**kwargs: object) -> dict[str, object]:
            return _execute(**kwargs)

        return sync_wrapped_handler

    def get_handler(self, name: str) -> ToolHandler | Callable[..., Awaitable[dict[str, object]]]:
        """Return the bound handler for one registered tool."""

        return self._handlers[name]

    def invoke(self, name: str, /, **kwargs: object) -> dict[str, object]:
        """Invoke one tool handler directly for tests and local orchestration."""

        handler = self.get_handler(name)
        if inspect.iscoroutinefunction(handler):
            return asyncio.run(handler(**kwargs))
        return cast("Callable[..., dict[str, object]]", handler)(**kwargs)


__all__ = ["QSpiceToolRuntime", "to_jsonable"]
