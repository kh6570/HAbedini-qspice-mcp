"""Service for removing one net label from a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import remove_net_label as remove_net_label_tag
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RemovedNetLabel:
    """Metadata for one removed net label."""

    schematic_path: Path
    output_path: Path
    position_x: int
    position_y: int
    net_name: str


SERVICE_SPEC = ServiceSpec(
    name="remove_net_label",
    title="Remove Net Label",
    summary="Remove one net label from a schematic by position and optional net name.",
    phase="implemented",
    read_only=False,
)


def remove_net_label(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    position_x: int,
    position_y: int,
    net_name: str | None = None,
    output_path: str | Path | None = None,
) -> RemovedNetLabel:
    """Remove one net label and persist the edited schematic."""

    normalized_net_name: str | None = None
    resolved_position: tuple[int, int] | None = None

    def apply_label_edit(editor: object) -> None:
        nonlocal normalized_net_name, resolved_position
        resolved_position = (position_x, position_y)
        normalized_net_name = remove_net_label_tag(
            cast("Any", editor),
            position=resolved_position,
            net_name=net_name,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_label_edit,
    )
    if normalized_net_name is None or resolved_position is None:
        raise RuntimeError("Net-label removal did not report a normalized net name.")
    return RemovedNetLabel(
        schematic_path=resolved_path,
        output_path=saved_path,
        position_x=resolved_position[0],
        position_y=resolved_position[1],
        net_name=normalized_net_name,
    )


__all__ = ["SERVICE_SPEC", "RemovedNetLabel", "remove_net_label"]
