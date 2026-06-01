"""Typing protocols shared by MCP tool mixins."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.mcp.tool_registry import ToolDefinition
    from qspice_mcp.services._internals.batch_manager import SimulationBatchManager
    from qspice_mcp.services._internals.live_gui_manager import LiveGuiSessionManager
    from qspice_mcp.services._internals.remote_session_manager import RemoteSimulationManager


class SupportsSettingsRuntime(Protocol):
    """Protocol for runtimes that expose normalized settings."""

    settings: QSpiceSettings


class SupportsBatchRuntime(SupportsSettingsRuntime, Protocol):
    """Protocol for runtimes that also expose batch lifecycle management."""

    _batch_manager: SimulationBatchManager


class SupportsRemoteRuntime(SupportsSettingsRuntime, Protocol):
    """Protocol for runtimes that also expose remote-style session management."""

    _remote_manager: RemoteSimulationManager


class SupportsLiveGuiRuntime(SupportsSettingsRuntime, Protocol):
    """Protocol for runtimes that also expose live GUI session management."""

    _live_gui_manager: LiveGuiSessionManager


class SupportsToolCatalogRuntime(SupportsSettingsRuntime, Protocol):
    """Protocol for runtimes that expose the registered tool catalog."""

    tools: tuple[ToolDefinition, ...]


__all__ = [
    "SupportsBatchRuntime",
    "SupportsLiveGuiRuntime",
    "SupportsRemoteRuntime",
    "SupportsSettingsRuntime",
    "SupportsToolCatalogRuntime",
]
