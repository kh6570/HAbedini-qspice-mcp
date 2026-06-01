"""Service for enumerating components from a schematic editor backend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.clean_room_schematic import (
    inspect_supported_schematic_components,
)
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSummary:
    """A normalized summary of one schematic component."""

    reference: str
    kind: str
    value: str | None
    description: str | None
    node_count: int
    has_subcircuit: bool


@dataclass(frozen=True, slots=True)
class ComponentCatalog:
    """Component inventory for one schematic."""

    schematic_path: Path
    component_count: int
    prefixes: str
    components: tuple[ComponentSummary, ...]


SERVICE_SPEC = ServiceSpec(
    name="list_components",
    title="List Components",
    summary=(
        "Enumerate components from a QSpice schematic through an installed "
        "editor backend or the supported clean-room subset."
    ),
    phase="implemented",
)


def _matches_prefixes(reference: str, prefixes: str) -> bool:
    return prefixes == "*" or reference[:1] in prefixes


def list_components(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    prefixes: str = "*",
) -> ComponentCatalog:
    """Enumerate schematic components using an editor backend or clean-room fallback."""

    resolved_workspace = workspace_root.resolve(strict=False)
    components: list[ComponentSummary] = []
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
        for parsed_component in inspect_supported_schematic_components(resolved_path):
            if not _matches_prefixes(parsed_component.reference, prefixes):
                continue
            components.append(
                ComponentSummary(
                    reference=parsed_component.reference,
                    kind=parsed_component.kind,
                    value=parsed_component.value,
                    description=parsed_component.description,
                    node_count=len(parsed_component.nodes),
                    has_subcircuit=parsed_component.has_subcircuit,
                )
            )
    else:
        references = tuple(str(reference) for reference in editor.get_components(prefixes=prefixes))
        for reference in references:
            editor_component = editor.get_component(reference)
            attributes = dict(editor_component.attributes)
            value = attributes.get("value")
            description = attributes.get("description")
            components.append(
                ComponentSummary(
                    reference=reference,
                    kind=str(attributes.get("type") or reference[:1]),
                    value=str(value) if value is not None else None,
                    description=str(description) if description is not None else None,
                    node_count=len(tuple(str(node) for node in editor_component.ports)),
                    has_subcircuit="_SUBCKT" in attributes,
                )
            )
    return ComponentCatalog(
        schematic_path=resolved_path,
        component_count=len(components),
        prefixes=prefixes,
        components=tuple(components),
    )


__all__ = ["SERVICE_SPEC", "ComponentCatalog", "ComponentSummary", "list_components"]
