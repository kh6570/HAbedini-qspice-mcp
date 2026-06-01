"""MCP protocol layer for qspice-mcp."""

from __future__ import annotations

from .definition import ServerDefinition, ServerParameter, build_server_definition
from .resources import ResourceDefinition, get_resource_definitions
from .server import QSpiceMCPServer, create_server, run
from .tool_registry import (
    ToolAnnotations,
    ToolDefinition,
    build_runtime_tool_registry,
    build_tool_registry,
    build_tool_registry_from_runtime,
    derive_input_schema,
    tool_def,
)
from .tools import QSpiceToolRuntime

__all__ = [
    "QSpiceMCPServer",
    "QSpiceToolRuntime",
    "ResourceDefinition",
    "ServerDefinition",
    "ServerParameter",
    "ToolAnnotations",
    "ToolDefinition",
    "build_runtime_tool_registry",
    "build_server_definition",
    "build_tool_registry",
    "build_tool_registry_from_runtime",
    "create_server",
    "derive_input_schema",
    "get_resource_definitions",
    "run",
    "tool_def",
]
