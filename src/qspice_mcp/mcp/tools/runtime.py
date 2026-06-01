"""Runtime-backed MCP tool handlers for implemented services."""

from __future__ import annotations

from functools import wraps
from time import perf_counter
from typing import TYPE_CHECKING

from qspice_mcp.infra.logging import get_logger
from qspice_mcp.infra.telemetry import attach_trace_id, request_scope
from qspice_mcp.services._internals.batch_manager import SimulationBatchManager
from qspice_mcp.services._internals.live_gui_manager import LiveGuiSessionManager
from qspice_mcp.services._internals.remote_session_manager import RemoteSimulationManager

from .artifacts import ARTIFACT_HANDLER_NAMES, ArtifactToolMixin
from .batch import BATCH_HANDLER_NAMES, BatchToolMixin
from .live_gui import LIVE_GUI_HANDLER_NAMES, LiveGuiToolMixin
from .mixed_signal import MIXED_SIGNAL_HANDLER_NAMES, MixedSignalToolMixin
from .protocol import PROTOCOL_HANDLER_NAMES, ProtocolToolMixin
from .remote import REMOTE_HANDLER_NAMES, RemoteToolMixin
from .recipes import RECIPES_HANDLER_NAMES, RecipesToolMixin
from .schematic import SCHEMATIC_HANDLER_NAMES, SchematicToolMixin
from .server_info import SERVER_INFO_HANDLER_NAMES, ServerInfoToolMixin
from .shared import to_jsonable
from .simulation import SIMULATION_HANDLER_NAMES, SimulationToolMixin
from .subcircuit import SUBCIRCUIT_HANDLER_NAMES, SubcircuitToolMixin
from .waveform import WAVEFORM_HANDLER_NAMES, WaveformToolMixin
from .workspace_files import WORKSPACE_FILES_HANDLER_NAMES, WorkspaceFilesToolMixin
from .workspace import (
    _WorkspaceSettingsProxy,
    get_pending_workspace_root,
    resolve_workspace_override,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from qspice_mcp.infra.config import QSpiceSettings

    from ..tool_registry import ToolDefinition

HANDLER_NAMES = (
    *SERVER_INFO_HANDLER_NAMES,
    *BATCH_HANDLER_NAMES,
    *REMOTE_HANDLER_NAMES,
    *ARTIFACT_HANDLER_NAMES,
    *LIVE_GUI_HANDLER_NAMES,
    *MIXED_SIGNAL_HANDLER_NAMES,
    *PROTOCOL_HANDLER_NAMES,
    *SCHEMATIC_HANDLER_NAMES,
    *SUBCIRCUIT_HANDLER_NAMES,
    *SIMULATION_HANDLER_NAMES,
    *WAVEFORM_HANDLER_NAMES,
    *RECIPES_HANDLER_NAMES,
    *WORKSPACE_FILES_HANDLER_NAMES,
)


class QSpiceToolRuntime(
    ServerInfoToolMixin,
    BatchToolMixin,
    RemoteToolMixin,
    ArtifactToolMixin,
    LiveGuiToolMixin,
    MixedSignalToolMixin,
    ProtocolToolMixin,
    SchematicToolMixin,
    SubcircuitToolMixin,
    SimulationToolMixin,
    WaveformToolMixin,
    RecipesToolMixin,
    WorkspaceFilesToolMixin,
):
    """Thin orchestration layer used by MCP tool handlers."""

    def __init__(self, settings: QSpiceSettings, tools: tuple[ToolDefinition, ...]) -> None:
        self.settings = settings.normalized()
        self.tools = tools
        self._batch_manager = SimulationBatchManager(self.settings)
        self._live_gui_manager = LiveGuiSessionManager(self.settings)
        self._remote_manager = RemoteSimulationManager(self.settings)
        self._tool_definitions = {tool.name: tool for tool in tools}
        self._handlers: dict[str, Callable[..., dict[str, object]]] = {
            name: self._wrap_handler(self._tool_definitions[name], getattr(self, name))
            for name in HANDLER_NAMES
        }

    def _wrap_handler(
        self,
        tool: ToolDefinition,
        handler: Callable[..., dict[str, object]],
    ) -> Callable[..., dict[str, object]]:
        logger = get_logger(component="mcp.tool", tool=tool.name)

        @wraps(handler)
        def wrapped_handler(**kwargs: object) -> dict[str, object]:
            workspace_override = resolve_workspace_override(kwargs.pop("workspace_root", None))
            if workspace_override is None:
                workspace_override = get_pending_workspace_root()
            original_settings = self.settings
            if workspace_override is not None:
                self.settings = _WorkspaceSettingsProxy(original_settings, workspace_override)
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
                result.setdefault("trace_id", trace_id)
                return result

        return wrapped_handler

    def get_handler(self, name: str) -> Callable[..., dict[str, object]]:
        """Return the bound handler for one registered tool."""

        return self._handlers[name]

    def invoke(self, name: str, /, **kwargs: object) -> dict[str, object]:
        """Invoke one tool handler directly for tests and local orchestration."""

        handler = self.get_handler(name)
        return handler(**kwargs)


__all__ = ["QSpiceToolRuntime", "to_jsonable"]
