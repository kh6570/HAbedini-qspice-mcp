# In the name of God, the Most Gracious, the Most Merciful
"""Tool definition registry for the MCP layer."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

from mcp_app_core.registry import build_tool_registry as build_core_tool_registry

from qspice_mcp.services._internals.service_catalog import build_service_spec_catalog
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Collection

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
    output_schema: dict[str, object] | None = None

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
        "Optional per-call workspace root. Both relative and absolute paths must stay "
        "inside this root; pass it explicitly when accessing a different circuit folder."
    ),
}

_PATH_PROPERTY_SUFFIXES = ("_path", "_dir", "_file", "_root")
_PATH_PROPERTY_NAMES = frozenset({"path", "dir", "directory", "file"})


def _has_path_like_property(properties: dict[str, object]) -> bool:
    """Return True when a schema declares a property that resolves against the workspace."""

    return any(
        name in _PATH_PROPERTY_NAMES or name.endswith(_PATH_PROPERTY_SUFFIXES)
        for name in properties
    )


_EXPECTED_HASH_PROPERTY: dict[str, object] = {
    "type": "string",
    "description": (
        "SHA-256 content hash from the last read of this schematic. "
        "When the file no longer matches, the save writes nothing."
    ),
}


def _normalize_input_schema(
    input_schema: dict[str, object],
    *,
    read_only: bool,
) -> dict[str, object]:
    """Ensure `required` is present and expose `workspace_root` only where paths resolve.

    The server accepts a `workspace_root` argument for every tool (it is popped
    before schema validation), but advertising it only on path-taking tools keeps
    the tools/list payload lean.
    """

    schema = dict(input_schema)
    existing_properties = schema.get("properties", {})
    properties: dict[str, object] = (
        dict(existing_properties) if isinstance(existing_properties, dict) else {}
    )
    if _has_path_like_property(properties) and "workspace_root" not in properties:
        properties["workspace_root"] = dict(_WORKSPACE_ROOT_SCHEMA_PROPERTY)
    if not read_only and "schematic_path" in properties and "expected_hash" not in properties:
        properties["expected_hash"] = dict(_EXPECTED_HASH_PROPERTY)
    schema["properties"] = properties
    schema.setdefault("required", [])
    return schema


@cache
def _load_planned_service_specs() -> tuple[ServiceSpec, ...]:
    """Discover service specs without importing ``qspice_mcp.services`` package init."""

    return build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))


def _select_specs(
    specs: tuple[ServiceSpec, ...],
    active_profiles: Collection[str] | None,
) -> tuple[ServiceSpec, ...]:
    """Keep specs whose profile is active. Omit the collection to keep every spec."""

    if active_profiles is None:
        return specs
    selected = build_core_tool_registry(specs, active_profiles=active_profiles)
    allowed = {tool.name for tool in selected}
    return tuple(spec for spec in specs if spec.name in allowed)


def build_tool_registry(
    service_specs: tuple[ServiceSpec, ...] | None = None,
    *,
    active_profiles: Collection[str] | None = None,
) -> tuple[ToolDefinition, ...]:
    """Build the planned tool registry from the service catalog.

    Omit ``active_profiles`` to include every spec. A normal session passes
    ``("default",)`` so extended groups stay unloaded.
    """

    specs = _select_specs(service_specs or _load_planned_service_specs(), active_profiles)
    tools: list[ToolDefinition] = []
    for spec in specs:
        if spec.input_schema is None:
            raise KeyError(f"Missing MCP input_schema for service {spec.name!r}.")
        tools.append(
            ToolDefinition(
                name=spec.name,
                title=spec.title,
                description=spec.description or spec.summary,
                input_schema=_normalize_input_schema(
                    dict(spec.input_schema),
                    read_only=spec.read_only,
                ),
                annotations=resolve_tool_annotations(spec),
                service=spec,
                output_schema=spec.output_schema,
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
