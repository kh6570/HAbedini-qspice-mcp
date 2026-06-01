"""Service for reading one component through a schematic editor backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.clean_room_schematic import (
    inspect_supported_schematic_components,
)
from qspice_mcp.services._backends.schematic_editor import (
    normalize_component_parameters,
    normalize_component_position,
    normalize_component_rotation,
    open_schematic_editor,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.subcircuit._clean_room import resolve_supported_subcircuit_target
from qspice_mcp.services.subcircuit._navigation import split_instance_component_reference

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentRead:
    """A normalized view of one schematic component."""

    schematic_path: Path
    reference: str
    kind: str
    value: str | None
    description: str | None
    nodes: tuple[str, ...]
    parameters: dict[str, str]
    raw_parameter_lines: tuple[str, ...]
    position_x: int
    position_y: int
    rotation_degrees: int
    has_subcircuit: bool


SERVICE_SPEC = ServiceSpec(
    name="read_component",
    title="Read Component",
    summary="Return a normalized view of one component from a QSpice schematic.",
    phase="implemented",
)


def read_component(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
) -> ComponentRead:
    """Read one schematic component using an editor backend or clean-room fallback."""

    resolved_workspace = workspace_root.resolve(strict=False)
    try:
        editor, resolved_path, _ = open_schematic_editor(
            schematic_path,
            workspace_root=resolved_workspace,
        )
    except BackendUnavailableError:
        resolved_path = validate_existing_file(
            schematic_path,
            workspace_root=resolved_workspace,
            suffixes=(".qsch",),
        )
        parsed_component = next(
            (
                item
                for item in inspect_supported_schematic_components(resolved_path)
                if item.reference == reference
            ),
            None,
        )
        normalized_reference = reference.strip()
        if parsed_component is None and ":" in normalized_reference:
            instance_path, subcircuit_reference, component_reference = (
                split_instance_component_reference(normalized_reference)
            )
            _, _, _, parsed_components = resolve_supported_subcircuit_target(
                resolved_path,
                workspace_root=resolved_workspace,
                reference=subcircuit_reference,
                instance_path=instance_path,
            )
            parsed_component = next(
                (item for item in parsed_components if item.reference == component_reference),
                None,
            )
            normalized_reference = ":".join(
                (*instance_path, subcircuit_reference, component_reference)
            )
        if parsed_component is None:
            raise ValueError(
                f"Component {reference} was not found in the supported clean-room schematic subset."
            ) from None
        return ComponentRead(
            schematic_path=resolved_path,
            reference=normalized_reference,
            kind=parsed_component.kind,
            value=parsed_component.value,
            description=parsed_component.description,
            nodes=parsed_component.nodes,
            parameters=parsed_component.parameters,
            raw_parameter_lines=parsed_component.raw_parameter_lines,
            position_x=parsed_component.position_x,
            position_y=parsed_component.position_y,
            rotation_degrees=parsed_component.rotation_degrees,
            has_subcircuit=parsed_component.has_subcircuit,
        )
    editor_component = editor.get_component(reference)
    attributes = dict(editor_component.attributes)
    raw_parameters = editor.get_component_parameters(reference)
    parameters, raw_parameter_lines = normalize_component_parameters(raw_parameters)
    nodes = tuple(str(node) for node in editor.get_component_nodes(reference))
    position, rotation = editor.get_component_position(reference)
    position_x, position_y = normalize_component_position(position)
    rotation_degrees = normalize_component_rotation(rotation)
    raw_value = attributes.get("value")
    if raw_value is None:
        raw_value = attributes.get("Value")
    if raw_value is None:
        raw_value = parameters.get("Value")
    value = str(raw_value) if raw_value is not None else None
    description = attributes.get("description")
    return ComponentRead(
        schematic_path=resolved_path,
        reference=reference,
        kind=str(attributes.get("type") or reference[:1]),
        value=value,
        description=str(description) if description is not None else None,
        nodes=nodes,
        parameters=parameters,
        raw_parameter_lines=raw_parameter_lines,
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=rotation_degrees,
        has_subcircuit="_SUBCKT" in attributes,
    )


__all__ = ["SERVICE_SPEC", "ComponentRead", "read_component"]
