"""Adapt generic MCP handlers to FastMCP-compatible signatures."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qspice_mcp.mcp.tool_registry import ToolDefinition

ToolHandler = Callable[..., dict[str, object]]


def expose_tool_schema(handler: ToolHandler, tool: ToolDefinition) -> ToolHandler:
    """Wrap one generic handler with an explicit signature derived from the tool schema."""

    schema = tool.input_schema
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    required = schema.get("required", [])
    required_names = {str(item) for item in required} if isinstance(required, list) else set[str]()

    parameters: list[inspect.Parameter] = []
    for name in properties:
        if name in required_names:
            default: object = inspect.Parameter.empty
        else:
            default = None
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                default=default,
                annotation=object,
            )
        )

    signature = inspect.Signature(parameters)

    def schema_handler(**kwargs: object) -> dict[str, object]:
        return handler(**kwargs)

    schema_handler.__name__ = tool.name
    schema_handler.__doc__ = tool.description
    schema_handler.__signature__ = signature.replace(return_annotation=dict[str, object])  # type: ignore[attr-defined]
    schema_handler.__annotations__ = {parameter.name: object for parameter in parameters} | {
        "return": dict[str, object]
    }
    return schema_handler


__all__ = ["ToolHandler", "expose_tool_schema"]
