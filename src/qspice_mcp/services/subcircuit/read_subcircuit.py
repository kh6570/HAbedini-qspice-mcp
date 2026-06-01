"""Service for reading one resolved subcircuit view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.subcircuit._clean_room import resolve_supported_subcircuit_target
from qspice_mcp.services.subcircuit._navigation import resolve_subcircuit_target

if TYPE_CHECKING:
    from pathlib import Path

SubcircuitScope = Literal["instance", "definition"]


@dataclass(frozen=True, slots=True)
class SubcircuitComponentSummary:
    """One normalized component summary inside a subcircuit."""

    reference: str
    kind: str
    value: str | None
    description: str | None
    node_count: int


@dataclass(frozen=True, slots=True)
class SubcircuitRead:
    """A resolved view of one subcircuit instance or definition."""

    schematic_path: Path
    instance_path: tuple[str, ...]
    reference: str
    scope: SubcircuitScope
    definition_name: str | None
    description: str | None
    component_count: int
    components: tuple[SubcircuitComponentSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="read_subcircuit",
    title="Read Subcircuit",
    summary="Return a resolved view of one subcircuit instance or definition.",
    phase="implemented",
)


def read_subcircuit(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    scope: SubcircuitScope = "instance",
    instance_path: tuple[str, ...] | list[str] | None = None,
) -> SubcircuitRead:
    """Read one subcircuit through the editor backend or clean-room fallback."""

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
        resolved_component, _, normalized_instance_path, parsed_components = (
            resolve_supported_subcircuit_target(
                resolved_path,
                workspace_root=resolved_workspace,
                reference=reference,
                instance_path=instance_path,
            )
        )
        warnings = (
            (
                "Instance scope was resolved through clean-room external .qsch lookup; "
                "per-instance backend expansion is unavailable without an installed "
                "schematic editor backend."
            )
            if scope == "instance"
            else "Definition scope was resolved through clean-room external .qsch lookup.",
        )
        return SubcircuitRead(
            schematic_path=resolved_path,
            instance_path=normalized_instance_path,
            reference=resolved_component.reference,
            scope=scope,
            definition_name=resolved_component.value,
            description=resolved_component.description,
            component_count=len(parsed_components),
            components=tuple(
                SubcircuitComponentSummary(
                    reference=parsed_component.reference,
                    kind=parsed_component.kind,
                    value=parsed_component.value,
                    description=parsed_component.description,
                    node_count=len(parsed_component.nodes),
                )
                for parsed_component in parsed_components
            ),
            warnings=warnings,
        )

    parent_editor, subeditor, normalized_instance_path, normalized_reference = (
        resolve_subcircuit_target(
            editor,
            reference=reference,
            instance_path=instance_path,
        )
    )
    component = parent_editor.get_component(normalized_reference)
    attributes = dict(component.attributes)
    value = attributes.get("value")
    description = attributes.get("description")

    references = tuple(str(name) for name in subeditor.get_components(prefixes="*"))
    components: list[SubcircuitComponentSummary] = []
    for child_reference in references:
        child = subeditor.get_component(child_reference)
        child_attributes = dict(child.attributes)
        child_value = child_attributes.get("value")
        child_description = child_attributes.get("description")
        components.append(
            SubcircuitComponentSummary(
                reference=child_reference,
                kind=str(child_attributes.get("type") or child_reference[:1]),
                value=str(child_value) if child_value is not None else None,
                description=str(child_description) if child_description is not None else None,
                node_count=len(tuple(str(node) for node in child.ports)),
            )
        )

    warnings = (
        "Instance scope is anchored at the selected subcircuit instance reference."
        if scope == "instance"
        else "Definition scope returns the shared subcircuit definition resolved by the backend.",
    )
    return SubcircuitRead(
        schematic_path=resolved_path,
        instance_path=normalized_instance_path,
        reference=normalized_reference,
        scope=scope,
        definition_name=str(value) if value is not None else None,
        description=str(description) if description is not None else None,
        component_count=len(components),
        components=tuple(components),
        warnings=warnings,
    )


__all__ = [
    "SERVICE_SPEC",
    "SubcircuitComponentSummary",
    "SubcircuitRead",
    "SubcircuitScope",
    "read_subcircuit",
]
