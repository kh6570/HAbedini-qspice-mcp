"""Service for inserting one net label into a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import add_net_label as add_net_label_tag
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedNetLabel:
    """Metadata for one inserted net label."""

    schematic_path: Path
    output_path: Path
    position_x: int
    position_y: int
    net_name: str


SERVICE_SPEC = ServiceSpec(
    name="add_net_label",
    title="Add Net Label",
    summary="Insert one net label into a schematic.",
    phase="implemented",
    read_only=False,
)


def add_net_label(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    position_x: int,
    position_y: int,
    net_name: str,
    output_path: str | Path | None = None,
) -> AddedNetLabel:
    """Insert one net label and persist the edited schematic."""

    normalized_net_name: str | None = None

    def apply_label_edit(editor: object) -> None:
        nonlocal normalized_net_name
        normalized_net_name = add_net_label_tag(
            cast("Any", editor),
            position=(position_x, position_y),
            net_name=net_name,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_label_edit,
    )
    if normalized_net_name is None:
        raise RuntimeError("Net-label insertion did not report a normalized net name.")
    return AddedNetLabel(
        schematic_path=resolved_path,
        output_path=saved_path,
        position_x=position_x,
        position_y=position_y,
        net_name=normalized_net_name,
    )


__all__ = ["SERVICE_SPEC", "AddedNetLabel", "add_net_label"]
