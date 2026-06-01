"""Tool definition registry for the MCP layer."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from functools import cache
from importlib import import_module
from typing import TYPE_CHECKING, Any, Literal, Union, get_args, get_origin

from qspice_mcp.services._internals.service_catalog import build_service_spec_catalog
from qspice_mcp.services.service_spec import ServiceSpec

from .tool_metadata import TOOL_METADATA

_DESCRIBE_SERVER_CAPABILITIES_SERVICE = ServiceSpec(
    name="describe_server_capabilities",
    title="Describe Server Capabilities",
    summary=(
        "Report server-level backend availability, degraded tool groups, and feature flags."
    ),
    phase="implemented",
)

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class ToolAnnotations:
    """Behavior hints for MCP clients."""

    read_only_hint: bool = False
    destructive_hint: bool = False
    idempotent_hint: bool = False
    open_world_hint: bool = False


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata for a planned MCP tool."""

    name: str
    title: str
    description: str
    input_schema: dict[str, object]
    annotations: ToolAnnotations
    service: ServiceSpec

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable summary of the tool."""

        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "service": self.service.name,
            "read_only": self.annotations.read_only_hint,
        }


def _coerce_annotations(raw: object) -> ToolAnnotations:
    if isinstance(raw, ToolAnnotations):
        return raw
    if not isinstance(raw, dict):
        return ToolAnnotations()
    return ToolAnnotations(
        read_only_hint=bool(raw.get("read_only_hint", False)),
        destructive_hint=bool(raw.get("destructive_hint", False)),
        idempotent_hint=bool(raw.get("idempotent_hint", False)),
        open_world_hint=bool(raw.get("open_world_hint", False)),
    )


_WORKSPACE_ROOT_SCHEMA_PROPERTY: dict[str, object] = {
    "type": "string",
    "description": (
        "Optional workspace root override for resolving relative paths in this call. "
        "Defaults to the server-configured workspace root."
    ),
}


def _with_workspace_root_property(input_schema: dict[str, object]) -> dict[str, object]:
    """Expose an optional per-call workspace root override in tool schemas."""

    schema = dict(input_schema)
    properties = dict(schema.get("properties", {}))
    if "workspace_root" not in properties:
        properties["workspace_root"] = dict(_WORKSPACE_ROOT_SCHEMA_PROPERTY)
    schema["properties"] = properties
    return schema


@cache
def _load_planned_service_specs() -> tuple[ServiceSpec, ...]:
    """Discover service specs without importing ``qspice_mcp.services`` package init."""

    return build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))


@cache
def _service_by_name() -> dict[str, ServiceSpec]:
    return {spec.name: spec for spec in _load_planned_service_specs()}


def build_tool_registry(
    service_specs: tuple[ServiceSpec, ...] | None = None,
) -> tuple[ToolDefinition, ...]:
    """Build the planned tool registry from the service catalog."""

    specs = service_specs or _load_planned_service_specs()
    tools: list[ToolDefinition] = []
    for spec in specs:
        metadata = TOOL_METADATA[spec.name]
        input_schema = metadata["input_schema"]
        if not isinstance(input_schema, dict):
            raise TypeError(f"Tool metadata for {spec.name} must expose a mapping input_schema.")
        tools.append(
            ToolDefinition(
                name=spec.name,
                title=str(metadata["title"]),
                description=str(metadata["description"]),
                input_schema=_with_workspace_root_property(dict(input_schema)),
                annotations=_coerce_annotations(metadata.get("annotations")),
                service=spec,
            )
        )
    return tuple(tools)


def build_runtime_tool_registry(
    tool_definitions: tuple[ToolDefinition, ...] | None = None,
) -> tuple[ToolDefinition, ...]:
    """Return only the tool definitions backed by implemented services."""

    definitions = tool_definitions or build_tool_registry()
    return tuple(tool for tool in definitions if tool.service.phase == "implemented")


_JSON_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}
_OPTIONAL_UNION_ARG_COUNT = 2


def _derive_json_type(annotation: type) -> dict[str, object]:  # noqa: PLR0911
    """Convert a Python type annotation to a JSON Schema fragment."""

    origin = get_origin(annotation)

    if origin is Union:
        args = get_args(annotation)
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1 and len(args) == _OPTIONAL_UNION_ARG_COUNT:
            schema = _derive_json_type(non_none[0])
            return {"oneOf": [schema, {"type": "null"}]}
        return {"oneOf": [_derive_json_type(arg) for arg in args]}

    if origin is Literal:
        return {"enum": list(get_args(annotation))}

    if origin in (list, tuple):
        item_args = get_args(annotation)
        item_type = item_args[0] if item_args else str
        return {"type": "array", "items": _derive_json_type(item_type)}

    if origin is dict:
        dict_args = get_args(annotation)
        value_type = dict_args[1] if len(dict_args) > 1 else str
        return {"type": "object", "additionalProperties": _derive_json_type(value_type)}

    if annotation in _JSON_TYPE_MAP:
        return {"type": _JSON_TYPE_MAP[annotation]}

    return {"type": "string"}


def derive_input_schema(func: Callable[..., object]) -> dict[str, object]:
    """Derive a JSON Schema from a function's type-annotated signature."""

    sig = inspect.signature(func)
    properties: dict[str, object] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            annotation = str

        properties[name] = _derive_json_type(annotation)
        if param.default is inspect.Parameter.empty:
            required.append(name)

    result: dict[str, object] = {"type": "object", "properties": properties}
    if required:
        result["required"] = required
    return result


def tool_def(
    title: str,
    description: str,
    annotations: ToolAnnotations | None = None,
    service_name: str | None = None,
) -> Callable[..., Any]:
    """Decorator that derives a ToolDefinition from a handler method's signature."""

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        input_schema = derive_input_schema(func)
        name = func.__name__
        service = _service_by_name().get(
            service_name or name,
            ServiceSpec(name=name, title=title, summary=description),
        )
        func._tool_definition = ToolDefinition(  # type: ignore[attr-defined]
            name=name,
            title=title,
            description=description,
            input_schema=input_schema,
            annotations=annotations or ToolAnnotations(),
            service=service,
        )
        return func

    return decorator


def build_tool_registry_from_runtime() -> tuple[ToolDefinition, ...]:
    """Build the tool registry by scanning ``QSpiceToolRuntime`` for decorated methods."""

    runtime_module = import_module("qspice_mcp.mcp.tools.runtime")
    runtime_type = runtime_module.QSpiceToolRuntime

    tools: list[ToolDefinition] = []
    for name in dir(runtime_type):
        if name.startswith("_"):
            continue
        method = getattr(runtime_type, name, None)
        if method is None or not callable(method):
            continue
        definition = getattr(method, "_tool_definition", None)
        if definition is not None:
            tools.append(definition)
    return tuple(tools)


__all__ = [
    "ToolAnnotations",
    "ToolDefinition",
    "build_runtime_tool_registry",
    "build_tool_registry",
    "build_tool_registry_from_runtime",
    "derive_input_schema",
    "tool_def",
]
