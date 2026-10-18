"""Schematic edit helpers: placement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from qspice_mcp.core.exceptions import QSpiceError

from ..schematic_editor_backend import (
    _format_qsch_point,
    _QschEditorProtocol,
    component_rotation_index_to_degrees,
)
from ..schematic_editor_geometry import resolve_component_pin_position
from .primitives import set_component_position
from .symbol_metadata import (
    read_component_symbol_metadata,
    set_component_symbol_text_attributes,
)
from .wiring import _parse_qsch_point


@dataclass(frozen=True, slots=True)
class WireFollowMove:
    """Result of moving one component while rewiring attached connection points."""

    position_x: int
    position_y: int
    rotation_degrees: int
    rewired_endpoints: int


def _component_position_xy(position: object) -> tuple[int, int]:
    """Read integer coordinates from a Point-like or tuple component position."""

    x_attr = getattr(position, "X", None)
    y_attr = getattr(position, "Y", None)
    if x_attr is not None and y_attr is not None:
        return int(x_attr), int(y_attr)
    sequence = cast("tuple[int, int]", position)
    return int(sequence[0]), int(sequence[1])


def _maybe_rewrite_point_token(
    tag: Any,
    token_index: int,
    coordinate_map: dict[tuple[int, int], tuple[int, int]],
) -> int:
    """Rewrite one QSch point token in place when it matches a remapped coordinate."""

    tokens = getattr(tag, "tokens", None)
    if tokens is None or len(tokens) <= token_index:
        return 0
    try:
        point = _parse_qsch_point(str(tokens[token_index]))
    except ValueError:
        return 0
    new_point = coordinate_map.get(point)
    if new_point is None:
        return 0
    tokens[token_index] = _format_qsch_point(new_point)
    return 1


def _rewrite_connection_points(
    editor: _QschEditorProtocol,
    coordinate_map: dict[tuple[int, int], tuple[int, int]],
) -> int:
    """Rewrite wire, junction, and net-label points that matched old pin coordinates."""

    if not coordinate_map or editor.schematic is None:
        return 0
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    rewired = 0
    for tag in items:
        tag_name = getattr(tag, "tag", None)
        if tag_name == "wire":
            rewired += _maybe_rewrite_point_token(tag, 1, coordinate_map)
            rewired += _maybe_rewrite_point_token(tag, 2, coordinate_map)
        elif tag_name in {"junction", "net"}:
            rewired += _maybe_rewrite_point_token(tag, 1, coordinate_map)
    if rewired:
        editor.updated = True
    return rewired


def move_component_preserving_connections(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    position_x: int | None = None,
    position_y: int | None = None,
    rotation_degrees: int | None = None,
) -> WireFollowMove:
    """Move/rotate one component and follow attached wire, junction, and net-label points."""

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")
    if position_x is None and position_y is None and rotation_degrees is None:
        raise ValueError("Provide at least one of position_x, position_y, or rotation_degrees.")

    component = editor.get_component(normalized_reference)
    pin_names = [str(port) for port in component.ports]
    old_positions: dict[str, tuple[int, int]] = {}
    for pin_name in pin_names:
        try:
            old_positions[pin_name] = resolve_component_pin_position(
                editor, reference=normalized_reference, pin_name=pin_name
            )
        except (ValueError, QSpiceError):
            continue

    current_position, _ = editor.get_component_position(normalized_reference)
    current_x, current_y = _component_position_xy(current_position)
    resolved_x = current_x if position_x is None else int(position_x)
    resolved_y = current_y if position_y is None else int(position_y)

    applied_x, applied_y, applied_degrees = set_component_position(
        editor,
        reference=normalized_reference,
        position_x=resolved_x,
        position_y=resolved_y,
        rotation_degrees=rotation_degrees,
    )

    coordinate_map: dict[tuple[int, int], tuple[int, int]] = {}
    for pin_name, old_point in old_positions.items():
        try:
            new_point = resolve_component_pin_position(
                editor, reference=normalized_reference, pin_name=pin_name
            )
        except (ValueError, QSpiceError):
            continue
        if new_point != old_point:
            coordinate_map[old_point] = new_point

    rewired = _rewrite_connection_points(editor, coordinate_map)
    return WireFollowMove(
        position_x=applied_x,
        position_y=applied_y,
        rotation_degrees=applied_degrees,
        rewired_endpoints=rewired,
    )


FACTORY_SYMBOL_TEXT_ROTATION_CODE = 7


UPRIGHT_SYMBOL_TEXT_ROTATION_CODE = 13


def symbol_text_rotation_code_for_degrees(degrees: int) -> int:
    """Encode one symbol-text orientation as a QSch rotation code (multiples of 90°)."""

    normalized = degrees % 360
    if normalized % 90 != 0:
        raise ValueError(f"degrees must be a multiple of 90; got {degrees}.")
    quarter_turns = normalized // 90
    return UPRIGHT_SYMBOL_TEXT_ROTATION_CODE + quarter_turns * 32


def _normalize_symbol_text_role_name(text_role: str) -> str:
    normalized = text_role.strip().lower()
    if normalized in {"reference", "refdes"}:
        return "reference"
    if normalized == "value":
        return "value"
    raise ValueError("text_roles entries must be 'reference', 'refdes', or 'value'.")


def _symbol_text_is_upright(
    rotation_code: int,
    *,
    target_rotation_code: int,
    component_rotation_degrees: int,
) -> bool:
    if rotation_code == target_rotation_code:
        return True
    return (
        component_rotation_degrees == 0
        and rotation_code == FACTORY_SYMBOL_TEXT_ROTATION_CODE
        and target_rotation_code == symbol_text_rotation_code_for_degrees(0)
    )


@dataclass(frozen=True, slots=True)
class NormalizedSymbolTextRotation:
    """One embedded symbol text row normalized to upright readability."""

    role: str
    previous_rotation_code: int
    rotation_code: int
    rotation_degrees: int | None
    updated: bool


def normalize_component_symbol_text_rotation(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    text_roles: tuple[str, ...] = ("reference", "value"),
    compensate_component_rotation: bool = True,
    upright_rotation_code: int | None = None,
) -> tuple[NormalizedSymbolTextRotation, ...]:
    """Reset refdes/value text rotation so labels read left-to-right in world space."""

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")
    if not text_roles:
        raise ValueError("text_roles must contain at least one role.")

    normalized_roles = {_normalize_symbol_text_role_name(role) for role in text_roles}
    _position, rotation_index_raw = editor.get_component_position(normalized_reference)
    del _position
    if not isinstance(rotation_index_raw, int):
        raise TypeError(f"Unsupported component rotation index: {rotation_index_raw!r}")
    component_rotation_degrees = component_rotation_index_to_degrees(rotation_index_raw)

    if compensate_component_rotation:
        target_rotation_code = symbol_text_rotation_code_for_degrees(
            (-component_rotation_degrees) % 360
        )
    elif upright_rotation_code is not None:
        target_rotation_code = upright_rotation_code
    else:
        target_rotation_code = symbol_text_rotation_code_for_degrees(0)

    metadata = read_component_symbol_metadata(editor, reference=normalized_reference)
    results: list[NormalizedSymbolTextRotation] = []
    for text_attribute in metadata.text_attributes:
        if text_attribute.role not in normalized_roles:
            continue
        previous_code = text_attribute.rotation_code
        if _symbol_text_is_upright(
            previous_code,
            target_rotation_code=target_rotation_code,
            component_rotation_degrees=component_rotation_degrees,
        ):
            results.append(
                NormalizedSymbolTextRotation(
                    role=text_attribute.role,
                    previous_rotation_code=previous_code,
                    rotation_code=previous_code,
                    rotation_degrees=text_attribute.rotation_degrees,
                    updated=False,
                )
            )
            continue
        updated = set_component_symbol_text_attributes(
            editor,
            reference=normalized_reference,
            text_index=text_attribute.index,
            rotation_code=target_rotation_code,
        )
        results.append(
            NormalizedSymbolTextRotation(
                role=updated.role,
                previous_rotation_code=previous_code,
                rotation_code=updated.rotation_code,
                rotation_degrees=updated.rotation_degrees,
                updated=True,
            )
        )
    return tuple(results)
