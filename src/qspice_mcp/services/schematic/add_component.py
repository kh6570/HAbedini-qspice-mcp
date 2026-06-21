"""Service for inserting one simple component into a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import add_simple_component
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.schematic._layout import DEFAULT_ORIGIN_X, DEFAULT_ORIGIN_Y
from qspice_mcp.services.schematic.suggest_component_placement import (
    suggest_component_placement,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedComponent:
    """Metadata for one inserted schematic component."""

    schematic_path: Path
    output_path: Path
    component_kind: str
    reference: str | None
    value: str | None
    position_x: int
    position_y: int
    rotation_degrees: int
    net_name: str | None


SERVICE_SPEC = ServiceSpec(
    name="add_component",
    title="Add Component",
    summary="Insert one simple part or ground label into a schematic.",
    phase="implemented",
    read_only=False,
)


def add_component(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    component_kind: str,
    reference: str | None = None,
    value: str | int | float | complex | None = None,
    position_x: int = 0,
    position_y: int = 0,
    rotation_degrees: int = 0,
    net_name: str | None = None,
    output_path: str | Path | None = None,
    auto_place: bool = False,
) -> AddedComponent:
    """Insert one supported simple component and persist the edited schematic."""

    effective_x = position_x
    effective_y = position_y
    effective_rotation = rotation_degrees
    if auto_place:
        suggestion = suggest_component_placement(
            schematic_path,
            workspace_root=workspace_root,
            component_kind=component_kind,
            origin_x=position_x if position_x != 0 else DEFAULT_ORIGIN_X,
            origin_y=position_y if position_y != 0 else DEFAULT_ORIGIN_Y,
        )
        effective_x = suggestion.position_x
        effective_y = suggestion.position_y
        if rotation_degrees == 0:
            effective_rotation = suggestion.rotation_degrees

    normalized_kind: str | None = None

    def apply_component_edit(editor: object) -> None:
        nonlocal normalized_kind
        normalized_kind = add_simple_component(
            cast("Any", editor),
            component_kind=component_kind,
            reference=reference,
            value=value,
            position=(effective_x, effective_y),
            rotation_degrees=effective_rotation,
            net_name=net_name,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_component_edit,
    )
    if normalized_kind is None:
        raise RuntimeError("Component insertion did not report a normalized component kind.")
    effective_net_name = None
    if normalized_kind == "ground":
        effective_net_name = (net_name or "GND").strip() or "GND"
    return AddedComponent(
        schematic_path=resolved_path,
        output_path=saved_path,
        component_kind=normalized_kind,
        reference=reference,
        value=None if value is None else str(value),
        position_x=effective_x,
        position_y=effective_y,
        rotation_degrees=effective_rotation,
        net_name=effective_net_name,
    )


__all__ = ["SERVICE_SPEC", "AddedComponent", "add_component"]
