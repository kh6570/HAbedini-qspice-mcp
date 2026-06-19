"""Service for moving one placed schematic component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    set_component_position as apply_component_position,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentPositionUpdate:
    """Metadata for one component placement edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    position_x: int
    position_y: int
    rotation_degrees: int


SERVICE_SPEC = ServiceSpec(
    name="set_component_position",
    title="Set Component Position",
    summary="Move one placed schematic component to new coordinates, optionally updating rotation.",
    phase="implemented",
    read_only=False,
)


def set_component_position(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    position_x: int,
    position_y: int,
    rotation_degrees: int | None = None,
    output_path: str | Path | None = None,
) -> ComponentPositionUpdate:
    """Move one component and persist the edited schematic."""

    applied: tuple[int, int, int] | None = None

    def apply_position_edit(editor: object) -> None:
        nonlocal applied
        applied = apply_component_position(
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
        apply_edit=apply_position_edit,
    )
    if applied is None:
        raise RuntimeError("Component position edit did not report applied coordinates.")
    return ComponentPositionUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        position_x=applied[0],
        position_y=applied[1],
        rotation_degrees=applied[2],
    )


__all__ = ["SERVICE_SPEC", "ComponentPositionUpdate", "set_component_position"]
