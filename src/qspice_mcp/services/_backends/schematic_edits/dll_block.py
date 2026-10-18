# In the name of God, the Most Gracious, the Most Merciful
"""Schematic edit helpers: dll block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from ..schematic_editor_backend import (
    _SYMBOL_PIN_AUX,
    _SYMBOL_PIN_COLOR,
    _SYMBOL_PIN_KIND,
    _SYMBOL_PIN_LABEL_ANCHOR,
    _SYMBOL_PIN_TEXT_SIZE,
    ComponentSymbolMetadata,
    SymbolPinMetadata,
    _format_qsch_point,
    _load_qsch_support_modules,
    _normalize_net_name,
    _normalize_pin_name,
    _normalize_qsch_color_code,
    _QschEditorProtocol,
    _quote_qsch_string,
    _SchematicComponentProtocol,
    normalize_component_position,
)
from .symbol_metadata import (
    _component_symbol_tag,
    _read_symbol_metadata_attr,
    _resolve_symbol_pin_tag,
    read_component_symbol_metadata,
)

_DLL_COMPONENT_REFERENCE_PREFIX = "X"


_DLL_COMPONENT_TYPE = "\u00d8(.DLL)"


_DLL_INPUT_PIN_KIND_CODE = 145


_DLL_OUTPUT_PIN_KIND_CODE = 146


_DLL_PIN_SPACING = 200


_DLL_LEFT_PIN_X = -800


_DLL_RIGHT_PIN_X = 600


_DLL_INPUT_LABEL_POSITION = (150, -50)


_DLL_OUTPUT_LABEL_POSITION = (-150, -50)


_DLL_RECT_LEFT_TOP = (-800, 200)


_DLL_RECT_RIGHT_X = 600


_DLL_PIN_TEXT_SIZE_TOKEN = 0.681


_DLL_PIN_LABEL_ANCHOR_CODE = 14


_DLL_PIN_COLOR_CODE = "0x0"


_DLL_PIN_AUX_CODE = -1


_DllPinDirection = Literal["input", "output"]


@dataclass(frozen=True, slots=True)
class _DllPinDefinition:
    """Internal normalized view of one `.DLL` block pin."""

    name: str
    direction: _DllPinDirection
    text_size_token: object = _DLL_PIN_TEXT_SIZE_TOKEN
    label_anchor_code: int = _DLL_PIN_LABEL_ANCHOR_CODE
    color_code: str = _DLL_PIN_COLOR_CODE
    aux_code: int = _DLL_PIN_AUX_CODE
    behavioral_net_override: str | None = None


def _normalize_dll_pin_names(
    pin_names: tuple[str, ...] | list[str],
) -> tuple[str, ...]:
    """Normalize one ordered list of DLL block pin names."""

    return tuple(_normalize_pin_name(str(pin_name)) for pin_name in pin_names)


def _build_dll_block_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    device_name: str,
    input_pin_names: tuple[str, ...],
    output_pin_names: tuple[str, ...],
) -> _SchematicComponentProtocol:
    """Create one `.DLL` block component object ready for insertion."""

    if not reference.upper().startswith(_DLL_COMPONENT_REFERENCE_PREFIX):
        raise ValueError(
            f".DLL block references must start with '{_DLL_COMPONENT_REFERENCE_PREFIX}'."
        )

    normalized_device_name = str(device_name).strip()
    if not normalized_device_name:
        raise ValueError("device_name must not be empty.")

    if not input_pin_names and not output_pin_names:
        raise ValueError("A .DLL block requires at least one input or output pin.")

    all_pin_names = (*input_pin_names, *output_pin_names)
    duplicate_names = {pin_name for pin_name in all_pin_names if all_pin_names.count(pin_name) > 1}
    if duplicate_names:
        duplicates = ", ".join(sorted(duplicate_names))
        raise ValueError(f".DLL block pin names must be unique. Duplicates: {duplicates}")

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    tag_class = qsch_module.QschTag
    component = base_schematic_module.SchematicComponent(editor, reference)
    component_tag = tag_class("component", "(0,0)", 0, 0)
    symbol_tag = tag_class("symbol")
    symbol_tag.items.append(tag_class("type:", _DLL_COMPONENT_TYPE))
    symbol_tag.items.append(tag_class("shorted pins:", "false"))

    max_pin_rows = max(len(input_pin_names), len(output_pin_names), 1)
    rect_bottom_y = _DLL_RECT_LEFT_TOP[1] - (_DLL_PIN_SPACING * (max_pin_rows + 1))
    symbol_tag.items.append(
        tag_class(
            "rect",
            _format_qsch_point(_DLL_RECT_LEFT_TOP),
            _format_qsch_point((_DLL_RECT_RIGHT_X, rect_bottom_y)),
            0,
            0,
            0,
            "0x4000000",
            "0x4000000",
            -1,
            1,
            -1,
        )
    )
    symbol_tag.items.append(tag_class("text", "(-100,-200)", 1, 12, 0, "0x1000000", -1, -1, '""'))
    symbol_tag.items.append(
        tag_class("text", "(-100,-300)", 0.681, 13, 0, "0x1000000", -1, -1, '""')
    )

    for index, pin_name in enumerate(input_pin_names):
        symbol_tag.items.append(
            tag_class(
                "pin",
                _format_qsch_point((_DLL_LEFT_PIN_X, -(index * _DLL_PIN_SPACING))),
                _format_qsch_point(_DLL_INPUT_LABEL_POSITION),
                0.681,
                14,
                _DLL_INPUT_PIN_KIND_CODE,
                "0x0",
                -1,
                _quote_qsch_string(pin_name),
            )
        )
    for index, pin_name in enumerate(output_pin_names):
        symbol_tag.items.append(
            tag_class(
                "pin",
                _format_qsch_point((_DLL_RIGHT_PIN_X, -(index * _DLL_PIN_SPACING))),
                _format_qsch_point(_DLL_OUTPUT_LABEL_POSITION),
                0.681,
                14,
                _DLL_OUTPUT_PIN_KIND_CODE,
                "0x0",
                -1,
                _quote_qsch_string(pin_name),
            )
        )
    component_tag.items.append(symbol_tag)

    texts = symbol_tag.get_items("text")
    texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(qsch_module.QSCH_TEXT_STR_ATTR, reference)
    texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].set_attr(
        qsch_module.QSCH_TEXT_STR_ATTR, normalized_device_name
    )

    component.reference = reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    component.attributes["type"] = _DLL_COMPONENT_TYPE
    component.attributes["value"] = normalized_device_name
    component.attributes["tag"] = component_tag
    component.attributes["enabled"] = True
    component.ports = [*input_pin_names, *output_pin_names]
    return cast("_SchematicComponentProtocol", component)


def _normalize_dll_pin_direction(direction: str) -> _DllPinDirection:
    """Normalize one `.DLL` pin direction token."""

    normalized = direction.strip().lower()
    if normalized not in {"input", "output"}:
        raise ValueError("direction must be either 'input' or 'output'.")
    return cast("_DllPinDirection", normalized)


def _ensure_dll_symbol(symbol_tag: Any, *, reference: str) -> None:
    """Reject pin-layout operations on non-`.DLL` symbols."""

    type_name = _read_symbol_metadata_attr(symbol_tag, "type:")
    if type_name != _DLL_COMPONENT_TYPE:
        raise ValueError(f"Component {reference} is not a `.DLL` block; found type {type_name!r}.")


def _dll_pin_direction_from_tag(pin_tag: Any, *, qsch_module: Any) -> _DllPinDirection:
    """Infer one `.DLL` pin direction from the raw tag."""

    pin_kind_code = int(pin_tag.get_attr(_SYMBOL_PIN_KIND))
    if pin_kind_code == _DLL_OUTPUT_PIN_KIND_CODE:
        return "output"
    if pin_kind_code == _DLL_INPUT_PIN_KIND_CODE:
        return "input"
    position_x, _ = normalize_component_position(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS1))
    return "input" if position_x < 0 else "output"


def _dll_pin_kind_code(direction: _DllPinDirection) -> int:
    """Return the QSch pin-kind code for one `.DLL` direction preset."""

    return _DLL_INPUT_PIN_KIND_CODE if direction == "input" else _DLL_OUTPUT_PIN_KIND_CODE


def _dll_pin_position(direction: _DllPinDirection, row_index: int) -> tuple[int, int]:
    """Return the local pin position for one `.DLL` row."""

    x_position = _DLL_LEFT_PIN_X if direction == "input" else _DLL_RIGHT_PIN_X
    return x_position, -(row_index * _DLL_PIN_SPACING)


def _dll_pin_label_position(direction: _DllPinDirection) -> tuple[int, int]:
    """Return the local label position for one `.DLL` direction."""

    return _DLL_INPUT_LABEL_POSITION if direction == "input" else _DLL_OUTPUT_LABEL_POSITION


def _dll_pin_definition_from_tag(pin_tag: Any, *, qsch_module: Any) -> _DllPinDefinition:
    """Build one normalized `.DLL` pin definition from a raw pin tag."""

    behavioral_net_override = (
        str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL)).strip()
        if len(pin_tag.tokens) > qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL
        else ""
    )
    return _DllPinDefinition(
        name=str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET)),
        direction=_dll_pin_direction_from_tag(pin_tag, qsch_module=qsch_module),
        text_size_token=pin_tag.tokens[_SYMBOL_PIN_TEXT_SIZE],
        label_anchor_code=int(pin_tag.get_attr(_SYMBOL_PIN_LABEL_ANCHOR)),
        color_code=_normalize_qsch_color_code(pin_tag.tokens[_SYMBOL_PIN_COLOR]),
        aux_code=int(pin_tag.get_attr(_SYMBOL_PIN_AUX)),
        behavioral_net_override=behavioral_net_override or None,
    )


def _read_dll_pin_definitions(
    symbol_tag: Any, *, qsch_module: Any
) -> tuple[_DllPinDefinition, ...]:
    """Read the current ordered `.DLL` pin definitions from one symbol tag."""

    return tuple(
        _dll_pin_definition_from_tag(pin_tag, qsch_module=qsch_module)
        for pin_tag in cast("list[Any]", symbol_tag.get_items("pin"))
    )


def _build_dll_pin_tag(qsch_module: Any, *, pin: _DllPinDefinition, row_index: int) -> Any:
    """Construct one raw `.DLL` symbol pin tag from a normalized definition."""

    pin_tag = qsch_module.QschTag(
        "pin",
        _format_qsch_point(_dll_pin_position(pin.direction, row_index)),
        _format_qsch_point(_dll_pin_label_position(pin.direction)),
        pin.text_size_token,
        pin.label_anchor_code,
        _dll_pin_kind_code(pin.direction),
        pin.color_code,
        pin.aux_code,
        _quote_qsch_string(pin.name),
    )
    if pin.behavioral_net_override is not None:
        pin_tag.tokens.append(_quote_qsch_string(_normalize_net_name(pin.behavioral_net_override)))
    return pin_tag


def _rewrite_dll_block_pin_tags(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    symbol_tag: Any,
    input_pins: tuple[_DllPinDefinition, ...],
    output_pins: tuple[_DllPinDefinition, ...],
    qsch_module: Any,
) -> ComponentSymbolMetadata:
    """Rewrite one `.DLL` symbol's pin tags and rect layout from grouped pin definitions."""

    ordered_pins = (*input_pins, *output_pins)
    if not ordered_pins:
        raise ValueError("A `.DLL` block must expose at least one pin.")

    symbol_items = cast("list[Any]", symbol_tag.items)
    first_pin_index = next(
        (index for index, item in enumerate(symbol_items) if str(item.tag) == "pin"),
        len(symbol_items),
    )
    symbol_items[:] = [item for item in symbol_items if str(item.tag) != "pin"]

    rebuilt_pin_tags = [
        *[
            _build_dll_pin_tag(qsch_module, pin=pin, row_index=index)
            for index, pin in enumerate(input_pins)
        ],
        *[
            _build_dll_pin_tag(qsch_module, pin=pin, row_index=index)
            for index, pin in enumerate(output_pins)
        ],
    ]
    symbol_items[first_pin_index:first_pin_index] = rebuilt_pin_tags

    rect_tags = cast("list[Any]", symbol_tag.get_items("rect"))
    if rect_tags:
        max_pin_rows = max(len(input_pins), len(output_pins), 1)
        rect_bottom_y = _DLL_RECT_LEFT_TOP[1] - (_DLL_PIN_SPACING * (max_pin_rows + 1))
        rect_tags[0].tokens[2] = _format_qsch_point((_DLL_RECT_RIGHT_X, rect_bottom_y))

    component = editor.get_component(reference)
    component.ports = [pin.name for pin in ordered_pins]
    editor.updated = True
    return read_component_symbol_metadata(editor, reference=reference)


def _find_dll_pin_metadata(
    metadata: ComponentSymbolMetadata, *, pin_name: str
) -> SymbolPinMetadata:
    """Return one pin metadata record by name after a `.DLL` pin rewrite."""

    normalized_pin_name = _normalize_pin_name(pin_name)
    for pin in metadata.pins:
        if pin.name == normalized_pin_name:
            return pin
    raise AssertionError(f"Updated `.DLL` pin {normalized_pin_name} was not found.")


def add_dll_block_pin_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    pin_name: str,
    direction: str,
    insert_index: int | None = None,
) -> tuple[SymbolPinMetadata, ComponentSymbolMetadata]:
    """Insert one `.DLL` block pin and return the new pin plus updated metadata."""

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    _ensure_dll_symbol(symbol_tag, reference=reference)

    normalized_pin_name = _normalize_pin_name(pin_name)
    normalized_direction = _normalize_dll_pin_direction(direction)
    existing_pins = list(_read_dll_pin_definitions(symbol_tag, qsch_module=qsch_module))
    if any(pin.name == normalized_pin_name for pin in existing_pins):
        raise ValueError(
            f"Component {reference} already has a symbol pin named {normalized_pin_name}."
        )

    input_pins = [pin for pin in existing_pins if pin.direction == "input"]
    output_pins = [pin for pin in existing_pins if pin.direction == "output"]
    target_pins = input_pins if normalized_direction == "input" else output_pins

    if insert_index is None:
        resolved_index = len(target_pins)
    else:
        if insert_index < 0 or insert_index > len(target_pins):
            raise ValueError(
                f"Component {reference} exposes {len(target_pins)} {normalized_direction} pin(s); "
                f"cannot insert at index {insert_index}."
            )
        resolved_index = insert_index

    target_pins.insert(
        resolved_index,
        _DllPinDefinition(name=normalized_pin_name, direction=normalized_direction),
    )
    updated_metadata = _rewrite_dll_block_pin_tags(
        editor,
        reference=reference,
        symbol_tag=symbol_tag,
        input_pins=tuple(input_pins),
        output_pins=tuple(output_pins),
        qsch_module=qsch_module,
    )
    return _find_dll_pin_metadata(updated_metadata, pin_name=normalized_pin_name), updated_metadata


def remove_dll_block_pin_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    pin_index: int | None = None,
    pin_name: str | None = None,
) -> tuple[SymbolPinMetadata, ComponentSymbolMetadata]:
    """Remove one `.DLL` block pin and return the removed pin plus updated metadata."""

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    _ensure_dll_symbol(symbol_tag, reference=reference)

    current_metadata = read_component_symbol_metadata(editor, reference=reference)
    resolved_index, _ = _resolve_symbol_pin_tag(
        symbol_tag,
        pin_index=pin_index,
        pin_name=pin_name,
        reference=reference,
    )
    removed_pin = current_metadata.pins[resolved_index]
    remaining_pins = list(_read_dll_pin_definitions(symbol_tag, qsch_module=qsch_module))
    remaining_pins.pop(resolved_index)
    if not remaining_pins:
        raise ValueError("A `.DLL` block must keep at least one pin.")

    updated_metadata = _rewrite_dll_block_pin_tags(
        editor,
        reference=reference,
        symbol_tag=symbol_tag,
        input_pins=tuple(pin for pin in remaining_pins if pin.direction == "input"),
        output_pins=tuple(pin for pin in remaining_pins if pin.direction == "output"),
        qsch_module=qsch_module,
    )
    return removed_pin, updated_metadata


def set_dll_block_pin_role_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    pin_index: int | None = None,
    pin_name: str | None = None,
    pin_role: str,
) -> tuple[SymbolPinMetadata, ComponentSymbolMetadata]:
    """Move one `.DLL` block pin into the input or output preset group."""

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    _ensure_dll_symbol(symbol_tag, reference=reference)

    resolved_index, _ = _resolve_symbol_pin_tag(
        symbol_tag,
        pin_index=pin_index,
        pin_name=pin_name,
        reference=reference,
    )
    normalized_direction = _normalize_dll_pin_direction(pin_role)
    pin_definitions = list(_read_dll_pin_definitions(symbol_tag, qsch_module=qsch_module))
    selected_pin = pin_definitions.pop(resolved_index)
    updated_pin = _DllPinDefinition(
        name=selected_pin.name,
        direction=normalized_direction,
        text_size_token=selected_pin.text_size_token,
        label_anchor_code=selected_pin.label_anchor_code,
        color_code=selected_pin.color_code,
        aux_code=selected_pin.aux_code,
        behavioral_net_override=selected_pin.behavioral_net_override,
    )

    input_pins = [pin for pin in pin_definitions if pin.direction == "input"]
    output_pins = [pin for pin in pin_definitions if pin.direction == "output"]
    if normalized_direction == "input":
        input_pins.append(updated_pin)
    else:
        output_pins.append(updated_pin)

    updated_metadata = _rewrite_dll_block_pin_tags(
        editor,
        reference=reference,
        symbol_tag=symbol_tag,
        input_pins=tuple(input_pins),
        output_pins=tuple(output_pins),
        qsch_module=qsch_module,
    )
    return _find_dll_pin_metadata(updated_metadata, pin_name=updated_pin.name), updated_metadata
