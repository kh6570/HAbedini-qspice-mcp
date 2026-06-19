"""Service for removing one junction node from a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import remove_junction as remove_junction_tag
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RemovedJunction:
    """Metadata for one removed junction node."""

    schematic_path: Path
    output_path: Path
    position_x: int
    position_y: int


SERVICE_SPEC = ServiceSpec(
    name="remove_junction",
    title="Remove Junction",
    summary="Remove one junction node from a schematic by position.",
    phase="implemented",
    read_only=False,
)


def remove_junction(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    position_x: int,
    position_y: int,
    output_path: str | Path | None = None,
) -> RemovedJunction:
    """Remove one junction and persist the edited schematic."""

    resolved_position: tuple[int, int] | None = None

    def apply_junction_edit(editor: object) -> None:
        nonlocal resolved_position
        resolved_position = remove_junction_tag(
            cast("Any", editor),
            position=(position_x, position_y),
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_junction_edit,
    )
    if resolved_position is None:
        raise RuntimeError("Junction removal did not report a position.")
    return RemovedJunction(
        schematic_path=resolved_path,
        output_path=saved_path,
        position_x=resolved_position[0],
        position_y=resolved_position[1],
    )


__all__ = ["SERVICE_SPEC", "RemovedJunction", "remove_junction"]
