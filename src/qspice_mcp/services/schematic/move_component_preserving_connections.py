"""Service for moving a component while keeping attached wires connected."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    move_component_preserving_connections as apply_wire_follow_move,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentConnectionMove:
    """Metadata for one wire-following component move."""

    schematic_path: Path
    output_path: Path
    reference: str
    position_x: int
    position_y: int
    rotation_degrees: int
    rewired_endpoints: int


SERVICE_SPEC = ServiceSpec(
    name="move_component_preserving_connections",
    title="Move Component Preserving Connections",
    summary=(
        "Deprecated alias: set_component_position now preserves connections by default. "
        "Move or rotate one component and follow attached wires, junctions, and net labels."
    ),
    phase="implemented",
    read_only=False,
)


def move_component_preserving_connections(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    position_x: int | None = None,
    position_y: int | None = None,
    rotation_degrees: int | None = None,
    output_path: str | Path | None = None,
) -> ComponentConnectionMove:
    """Move one component and rewrite attached connection points, then persist the schematic."""

    applied: Any = None

    def apply_move_edit(editor: object) -> None:
        nonlocal applied
        applied = apply_wire_follow_move(
            cast("Any", editor),
            reference=reference,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_move_edit,
    )
    if applied is None:
        raise RuntimeError("Component move edit did not report applied coordinates.")
    return ComponentConnectionMove(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        position_x=applied.position_x,
        position_y=applied.position_y,
        rotation_degrees=applied.rotation_degrees,
        rewired_endpoints=applied.rewired_endpoints,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentConnectionMove",
    "move_component_preserving_connections",
]
