"""MCP tool metadata and runtime handlers for qspice-mcp."""

from __future__ import annotations

from functools import cache

from qspice_mcp.mcp.tool_registry import (
    ToolDefinition,
    build_runtime_tool_registry,
    build_tool_registry,
)
from qspice_mcp.mcp.tools.live_gui import LiveGuiToolMixin
from qspice_mcp.mcp.tools.mixed_signal import MixedSignalToolMixin
from qspice_mcp.mcp.tools.protocol import ProtocolToolMixin
from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime, to_jsonable


@cache
def _planned_tools() -> tuple[ToolDefinition, ...]:
    return build_tool_registry()


@cache
def _runtime_tools() -> tuple[ToolDefinition, ...]:
    return build_runtime_tool_registry(_planned_tools())


def __getattr__(name: str) -> tuple[ToolDefinition, ...]:
    if name == "PLANNED_TOOLS":
        return _planned_tools()
    if name == "RUNTIME_TOOLS":
        return _runtime_tools()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "PLANNED_TOOLS",
    "RUNTIME_TOOLS",
    "LiveGuiToolMixin",
    "MixedSignalToolMixin",
    "ProtocolToolMixin",
    "QSpiceToolRuntime",
    "ToolDefinition",
    "build_runtime_tool_registry",
    "build_tool_registry",
    "to_jsonable",
]
