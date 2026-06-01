"""Geometry helpers for schematic editing operations."""

from __future__ import annotations

import math
from typing import Any, cast

from qspice_mcp.core.exceptions import QSpiceError

from .schematic_editor_backend import (
    _MIRROR_ROTATION_INDEX_MAX,
    _MIRROR_ROTATION_OFFSET,
    _PIN_POSITION_ROUNDING_DIGITS,
    _ROTATION_INDEX_MAX,
    _ROTATION_STEP_DEGREES,
    _load_qsch_support_modules,
    _normalize_pin_name,
    _QschEditorProtocol,
    normalize_component_position,
)


def resolve_component_pin_position(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    pin_name: str,
) -> tuple[int, int]:
    """Resolve one component pin name to an absolute schematic coordinate."""

    normalized_pin_name = _normalize_pin_name(pin_name)
    qsch_module, _ = _load_qsch_support_modules()
    component = editor.get_component(reference)
    component_tag = cast("Any", component.attributes["tag"])
    symbol_tags = component_tag.get_items("symbol")
    if not symbol_tags:
        raise QSpiceError(f"Component {reference} does not expose a symbol tag.")
    symbol_tag = symbol_tags[0]
    pin_tags = symbol_tag.get_items("pin")
    if not pin_tags:
        raise QSpiceError(f"Component {reference} does not expose any pins.")

    local_pin_position: tuple[int, int] | None = None
    available_pins: list[str] = []
    for pin_tag in pin_tags:
        available_pin_name = str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET))
        available_pins.append(available_pin_name)
        if available_pin_name != normalized_pin_name:
            continue
        local_pin_position = normalize_component_position(
            pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS1)
        )
        break

    if local_pin_position is None:
        available = ", ".join(sorted(available_pins))
        raise ValueError(
            f"Component {reference} has no pin named {normalized_pin_name}. "
            f"Available pins: {available}"
        )

    component_position = normalize_component_position(component_tag.get_attr(1))
    orientation = int(component_tag.get_attr(2))
    hypotenuse = math.hypot(local_pin_position[0], local_pin_position[1])
    if 0 <= orientation <= _ROTATION_INDEX_MAX:
        theta = math.atan2(local_pin_position[1], local_pin_position[0]) + math.radians(
            orientation * _ROTATION_STEP_DEGREES
        )
        resolved_x = component_position[0] + round(
            hypotenuse * math.cos(theta),
            _PIN_POSITION_ROUNDING_DIGITS,
        )
        resolved_y = component_position[1] + round(
            hypotenuse * math.sin(theta),
            _PIN_POSITION_ROUNDING_DIGITS,
        )
    elif _MIRROR_ROTATION_OFFSET <= orientation <= _MIRROR_ROTATION_INDEX_MAX:
        theta = math.atan2(local_pin_position[1], local_pin_position[0]) + math.radians(
            (orientation - _MIRROR_ROTATION_OFFSET) * _ROTATION_STEP_DEGREES
        )
        resolved_x = component_position[0] - round(
            hypotenuse * math.cos(theta),
            _PIN_POSITION_ROUNDING_DIGITS,
        )
        resolved_y = component_position[1] + round(
            hypotenuse * math.sin(theta),
            _PIN_POSITION_ROUNDING_DIGITS,
        )
    else:
        raise ValueError(f"Unsupported component orientation: {orientation}")
    return int(resolved_x), int(resolved_y)


def _resolve_wire_endpoint(
    editor: _QschEditorProtocol,
    *,
    endpoint_name: str,
    position: tuple[int, int] | None,
    reference: str | None,
    pin_name: str | None,
) -> tuple[int, int]:
    """Resolve one wire endpoint from raw coordinates or a reference/pin pair."""

    has_position = position is not None
    has_pin_selector = reference is not None or pin_name is not None

    if has_position and has_pin_selector:
        raise ValueError(
            f"Wire {endpoint_name} must use either coordinates or a reference/pin selector, "
            "not both."
        )
    if position is not None:
        return position
    if not has_pin_selector:
        raise ValueError(
            f"Wire {endpoint_name} must provide either coordinates or both "
            f"{endpoint_name}_reference and {endpoint_name}_pin."
        )
    if reference is None or pin_name is None:
        raise ValueError(
            f"Wire {endpoint_name} pin selection requires both {endpoint_name}_reference "
            f"and {endpoint_name}_pin."
        )
    return resolve_component_pin_position(editor, reference=reference, pin_name=pin_name)


def resolve_wire_points(
    editor: _QschEditorProtocol,
    *,
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Resolve both wire endpoints from raw coordinates or reference/pin selectors."""

    start_position = _resolve_wire_endpoint(
        editor,
        endpoint_name="start",
        position=start,
        reference=start_reference,
        pin_name=start_pin,
    )
    end_position = _resolve_wire_endpoint(
        editor,
        endpoint_name="end",
        position=end,
        reference=end_reference,
        pin_name=end_pin,
    )
    if start_position == end_position:
        raise ValueError("Wire start and end positions must be different.")
    return start_position, end_position
