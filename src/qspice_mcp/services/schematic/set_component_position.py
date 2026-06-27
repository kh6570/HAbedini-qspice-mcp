"""Service for placing one schematic component (move and/or rotate).

This is the unified placement tool. By default it preserves attached
connections (wires, junctions, net labels follow the moved/rotated pins) and
normalizes refdes/value text to upright readability — the two follow-up steps
agents used to have to remember. Both behaviors have opt-out flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services._backends.schematic_editor import (
    move_component_preserving_connections as apply_wire_follow_move,
)
from qspice_mcp.services._backends.schematic_editor import (
    normalize_component_symbol_text_rotation as apply_symbol_text_normalization,
)
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
    preserve_connections: bool = True
    rewired_endpoints: int = 0
    normalize_text: bool = True
    normalized_text_count: int = 0


SERVICE_SPEC = ServiceSpec(
    name="set_component_position",
    title="Set Component Position",
    summary=(
        "Move and/or rotate one placed component. By default attached wires, junctions, "
        "and net labels follow the pins (preserve_connections) and refdes/value text is "
        "reset to upright readability (normalize_text). This is the unified placement tool."
    ),
    phase="implemented",
    read_only=False,
)


def _read_current_xy(editor: Any, reference: str) -> tuple[int, int]:
    position, _rotation = editor.get_component_position(reference.strip())
    x_attr = getattr(position, "X", None)
    y_attr = getattr(position, "Y", None)
    if x_attr is not None and y_attr is not None:
        return int(x_attr), int(y_attr)
    sequence = cast("tuple[int, int]", position)
    return int(sequence[0]), int(sequence[1])


def set_component_position(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    position_x: int | None = None,
    position_y: int | None = None,
    rotation_degrees: int | None = None,
    preserve_connections: bool = True,
    normalize_text: bool = True,
    output_path: str | Path | None = None,
) -> ComponentPositionUpdate:
    """Move and/or rotate one component, persisting the edited schematic.

    Provide at least one of ``position_x``, ``position_y``, or ``rotation_degrees``.
    """

    if position_x is None and position_y is None and rotation_degrees is None:
        raise ValueError("Provide at least one of position_x, position_y, or rotation_degrees.")

    applied_x: int | None = None
    applied_y: int | None = None
    applied_degrees: int | None = None
    rewired_endpoints = 0
    normalized_text_count = 0

    def apply_placement_edit(editor: object) -> None:
        nonlocal applied_x, applied_y, applied_degrees, rewired_endpoints, normalized_text_count
        editor_obj = cast("Any", editor)

        if preserve_connections:
            move = apply_wire_follow_move(
                editor_obj,
                reference=reference,
                position_x=position_x,
                position_y=position_y,
                rotation_degrees=rotation_degrees,
            )
            applied_x = move.position_x
            applied_y = move.position_y
            applied_degrees = move.rotation_degrees
            rewired_endpoints = move.rewired_endpoints
        else:
            resolved_x, resolved_y = position_x, position_y
            if resolved_x is None or resolved_y is None:
                current_x, current_y = _read_current_xy(editor_obj, reference)
                resolved_x = current_x if resolved_x is None else int(resolved_x)
                resolved_y = current_y if resolved_y is None else int(resolved_y)
            applied_x, applied_y, applied_degrees = apply_component_position(
                editor_obj,
                reference=reference,
                position_x=int(resolved_x),
                position_y=int(resolved_y),
                rotation_degrees=rotation_degrees,
            )

        if normalize_text:
            try:
                normalized_rows = apply_symbol_text_normalization(
                    editor_obj,
                    reference=reference,
                    compensate_component_rotation=True,
                )
            except (QSpiceError, ValueError):
                normalized_rows = ()
            normalized_text_count = sum(1 for row in normalized_rows if row.updated)

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_placement_edit,
    )
    if applied_x is None or applied_y is None or applied_degrees is None:
        raise RuntimeError("Component placement edit did not report applied coordinates.")
    return ComponentPositionUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference.strip(),
        position_x=applied_x,
        position_y=applied_y,
        rotation_degrees=applied_degrees,
        preserve_connections=preserve_connections,
        rewired_endpoints=rewired_endpoints,
        normalize_text=normalize_text,
        normalized_text_count=normalized_text_count,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentPositionUpdate",
    "set_component_position",
]
