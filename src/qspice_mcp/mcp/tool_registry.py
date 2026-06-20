"""Tool definition registry for the MCP layer."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from qspice_mcp.services._internals.service_catalog import build_service_spec_catalog
from qspice_mcp.services.service_spec import ServiceSpec

_DESCRIBE_SERVER_CAPABILITIES_SERVICE = ServiceSpec(
    name="describe_server_capabilities",
    title="Describe Server Capabilities",
    summary=("Report server-level backend availability, degraded tool groups, and feature flags."),
    phase="implemented",
)

_OPEN_WORLD_TOOL_NAMES = frozenset(
    {
        "build_dll_device",
        "close_live_gui_session",
        "launch_live_gui_session",
        "poll_live_gui_session",
        "poll_live_gui_session_events",
        "run_monte_carlo",
        "run_model_sweep",
        "run_param_sweep",
        "run_simulation",
        "run_value_sweep",
        "run_worst_case",
        "send_live_gui_session_command",
        "submit_batch",
        "submit_remote_simulation",
        "write_workspace_text_file",
    }
)


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


def resolve_tool_annotations(spec: ServiceSpec) -> ToolAnnotations:
    """Derive MCP tool annotation hints from one enriched service spec."""

    open_world = spec.long_running or spec.name in _OPEN_WORLD_TOOL_NAMES
    return ToolAnnotations(
        read_only_hint=spec.read_only,
        destructive_hint=spec.destructive,
        idempotent_hint=spec.idempotent if spec.idempotent is not None else spec.read_only,
        open_world_hint=open_world,
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
    existing_properties = schema.get("properties", {})
    properties: dict[str, object] = (
        dict(existing_properties) if isinstance(existing_properties, dict) else {}
    )
    if "workspace_root" not in properties:
        properties["workspace_root"] = dict(_WORKSPACE_ROOT_SCHEMA_PROPERTY)
    schema["properties"] = properties
    return schema


@cache
def _load_planned_service_specs() -> tuple[ServiceSpec, ...]:
    """Discover service specs without importing ``qspice_mcp.services`` package init."""

    return build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))


def build_tool_registry(
    service_specs: tuple[ServiceSpec, ...] | None = None,
) -> tuple[ToolDefinition, ...]:
    """Build the planned tool registry from the service catalog."""

    specs = service_specs or _load_planned_service_specs()
    tools: list[ToolDefinition] = []
    for spec in specs:
        if spec.input_schema is None:
            raise KeyError(f"Missing MCP input_schema for service {spec.name!r}.")
        tools.append(
            ToolDefinition(
                name=spec.name,
                title=spec.title,
                description=spec.description or spec.summary,
                input_schema=_with_workspace_root_property(dict(spec.input_schema)),
                annotations=resolve_tool_annotations(spec),
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


__all__ = [
    "ToolAnnotations",
    "ToolDefinition",
    "build_runtime_tool_registry",
    "build_tool_registry",
    "resolve_tool_annotations",
]
