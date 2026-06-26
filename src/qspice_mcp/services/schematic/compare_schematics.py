"""Service for diffing two supported schematics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.clean_room_schematic import (
    inspect_supported_schematic_components,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic._connectivity import build_connectivity
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.clean_room_schematic import CleanRoomComponentInspection


@dataclass(frozen=True, slots=True)
class ComponentFieldChange:
    """One changed field on a component shared by both schematics."""

    reference: str
    field: str
    base: str | None
    revised: str | None


@dataclass(frozen=True, slots=True)
class SchematicComparison:
    """Structured diff between a base and revised schematic."""

    base_path: Path
    revised_path: Path
    added_components: tuple[str, ...]
    removed_components: tuple[str, ...]
    changed_components: tuple[ComponentFieldChange, ...]
    base_node_count: int
    revised_node_count: int
    identical: bool


SERVICE_SPEC = ServiceSpec(
    name="compare_schematics",
    title="Compare Schematics",
    summary="Diff two supported schematics by components (value, model, position) and net counts.",
    phase="implemented",
    read_only=True,
)


def _index(
    inspections: tuple[CleanRoomComponentInspection, ...],
) -> dict[str, CleanRoomComponentInspection]:
    return {item.reference: item for item in inspections}


def _component_changes(
    base: CleanRoomComponentInspection,
    revised: CleanRoomComponentInspection,
) -> list[ComponentFieldChange]:
    changes: list[ComponentFieldChange] = []
    base_position = f"({base.position_x},{base.position_y})"
    revised_position = f"({revised.position_x},{revised.position_y})"
    fields: tuple[tuple[str, str | None, str | None], ...] = (
        ("kind", base.kind, revised.kind),
        ("value", base.value, revised.value),
        ("position", base_position, revised_position),
        ("rotation_degrees", str(base.rotation_degrees), str(revised.rotation_degrees)),
        ("nodes", ",".join(base.nodes), ",".join(revised.nodes)),
    )
    for field_name, base_value, revised_value in fields:
        if base_value != revised_value:
            changes.append(
                ComponentFieldChange(
                    reference=base.reference,
                    field=field_name,
                    base=base_value,
                    revised=revised_value,
                )
            )
    return changes


def compare_schematics(
    base_path: str | Path,
    revised_path: str | Path,
    *,
    workspace_root: Path,
) -> SchematicComparison:
    """Return a structured diff between two supported clean-room schematics."""

    resolved_workspace = workspace_root.resolve(strict=False)
    resolved_base = validate_existing_file(
        base_path, workspace_root=resolved_workspace, suffixes=(".qsch",)
    )
    resolved_revised = validate_existing_file(
        revised_path, workspace_root=resolved_workspace, suffixes=(".qsch",)
    )

    base_index = _index(inspect_supported_schematic_components(resolved_base))
    revised_index = _index(inspect_supported_schematic_components(resolved_revised))

    added = tuple(sorted(set(revised_index) - set(base_index)))
    removed = tuple(sorted(set(base_index) - set(revised_index)))

    changed: list[ComponentFieldChange] = []
    for reference in sorted(set(base_index) & set(revised_index)):
        changed.extend(_component_changes(base_index[reference], revised_index[reference]))

    base_nodes = build_connectivity(resolved_base).node_count
    revised_nodes = build_connectivity(resolved_revised).node_count

    return SchematicComparison(
        base_path=resolved_base,
        revised_path=resolved_revised,
        added_components=added,
        removed_components=removed,
        changed_components=tuple(changed),
        base_node_count=base_nodes,
        revised_node_count=revised_nodes,
        identical=not added and not removed and not changed and base_nodes == revised_nodes,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentFieldChange",
    "SchematicComparison",
    "compare_schematics",
]
