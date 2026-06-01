"""Service for inserting one junction node into a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import add_junction as add_junction_tag
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedJunction:
    """Metadata for one inserted schematic junction."""

    schematic_path: Path
    output_path: Path
    position_x: int
    position_y: int


SERVICE_SPEC = ServiceSpec(
    name="add_junction",
    title="Add Junction",
    summary="Insert one junction node into a schematic wire graph.",
    phase="implemented",
    read_only=False,
)


def add_junction(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    position_x: int,
    position_y: int,
    output_path: str | Path | None = None,
) -> AddedJunction:
    """Insert one junction and persist the edited schematic."""

    resolved_position: tuple[int, int] | None = None

    def apply_junction_edit(editor: object) -> None:
        nonlocal resolved_position
        resolved_position = add_junction_tag(
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
        raise RuntimeError("Junction insertion did not report a position.")
    return AddedJunction(
        schematic_path=resolved_path,
        output_path=saved_path,
        position_x=resolved_position[0],
        position_y=resolved_position[1],
    )


__all__ = ["SERVICE_SPEC", "AddedJunction", "add_junction"]
