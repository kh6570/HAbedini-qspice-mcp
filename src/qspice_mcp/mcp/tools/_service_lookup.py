"""Resolve MCP service callables through tool-group shim modules."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, cast

from qspice_mcp.services._internals.service_catalog import resolve_service_module

if TYPE_CHECKING:
    from collections.abc import Callable

_SHIM_MODULE_PATHS: tuple[str, ...] = (
    "qspice_mcp.mcp.tools.server_info",
    "qspice_mcp.mcp.tools.batch",
    "qspice_mcp.mcp.tools.remote",
    "qspice_mcp.mcp.tools.artifacts",
    "qspice_mcp.mcp.tools.live_gui",
    "qspice_mcp.mcp.tools.mixed_signal",
    "qspice_mcp.mcp.tools.protocol",
    "qspice_mcp.mcp.tools.schematic",
    "qspice_mcp.mcp.tools.subcircuit",
    "qspice_mcp.mcp.tools.simulation",
    "qspice_mcp.mcp.tools.waveform",
    "qspice_mcp.mcp.tools.recipes",
    "qspice_mcp.mcp.tools.workspace_files",
)

_RUNTIME_ALIASES: dict[str, str] = {
    "describe_server_capabilities": "describe_server_capabilities_runtime",
}


def resolve_mcp_service_callable(tool_name: str) -> Callable[..., object]:
    """Return the service callable used by one MCP tool handler."""

    alias = _RUNTIME_ALIASES.get(tool_name, f"{tool_name}_service")
    for module_path in _SHIM_MODULE_PATHS:
        module = import_module(module_path)
        candidate = getattr(module, alias, None)
        if callable(candidate):
            return cast("Callable[..., object]", candidate)
    service_module = resolve_service_module(tool_name)
    service_fn = getattr(service_module, tool_name, None)
    if not callable(service_fn):
        raise TypeError(f"Service module {service_module.__name__} lacks callable {tool_name}.")
    return cast("Callable[..., object]", service_fn)


__all__ = ["resolve_mcp_service_callable"]
