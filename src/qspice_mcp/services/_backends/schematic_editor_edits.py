"""Symbol and edit operations for QschEditor-backed schematic services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from qspice_mcp.core.exceptions import ArtifactMissingError, QSpiceError

from .clean_room_schematic import write_blank_schematic
from .schematic_editor_backend import (
    _BEHAVIORAL_REFERENCE_PREFIX,
    _CAPACITOR_REFERENCE_PREFIX,
    _DIODE_REFERENCE_PREFIX,
    _GROUND_NET_NAME,
    _IMAGE_FILE_SUFFIXES,
    _INDUCTOR_REFERENCE_PREFIX,
    _MOSFET_REFERENCE_PREFIX,
    _NET_LABEL_FLAGS,
    _NET_LABEL_KIND,
    _NET_LABEL_STYLE_DEFAULT,
    _NET_LABEL_STYLE_GROUND,
    _RESISTOR_REFERENCE_PREFIX,
    _SYMBOL_METADATA_TAGS,
    _SYMBOL_PIN_AUX,
    _SYMBOL_PIN_COLOR,
    _SYMBOL_PIN_KIND,
    _SYMBOL_PIN_LABEL_ANCHOR,
    _SYMBOL_PIN_TEXT_SIZE,
    _VOLTAGE_SOURCE_REFERENCE_PREFIX,
    ComponentSymbolMetadata,
    SimpleComponentKind,
    SymbolDrawingMetadata,
    SymbolPinMetadata,
    SymbolTextMetadata,
    _coerce_qsch_color_code,
    _format_qsch_point,
    _load_qsch_support_modules,
    _normalize_component_kind,
    _normalize_net_name,
    _normalize_optional_bool,
    _normalize_pin_name,
    _normalize_qsch_color_code,
    _QschEditorProtocol,
    _quote_qsch_string,
    _SchematicComponentProtocol,
    _unquote_qsch_string,
    component_rotation_degrees_to_index,
    component_rotation_index_to_degrees,
    load_qsch_editor_factory,
    normalize_component_position,
    resolve_schematic_output_path,
)
from .schematic_editor_geometry import resolve_wire_points

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def _symbol_text_role(index: int) -> str:
    """Resolve one symbol text index to a stable role name."""

    if index == 0:
        return "reference"
    if index == 1:
        return "value"
    return "custom"


def _symbol_rotation_degrees(rotation_code: int) -> int | None:
    """Translate one QSch text rotation code into degrees when it matches the known pattern."""

    delta = rotation_code - 13
    if delta < 0 or delta % 32 != 0:
        return None
    return (delta // 32) * 90


def _component_symbol_tag(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> tuple[Any, Any]:
    """Resolve the raw component and embedded symbol tags for one reference."""

    component = editor.get_component(reference)
    component_tag = cast("Any", component.attributes.get("tag"))
    if component_tag is None:
        raise QSpiceError(f"Component {reference} does not expose a raw tag tree.")
    symbol_tags = component_tag.get_items("symbol")
    if not symbol_tags:
        raise QSpiceError(f"Component {reference} does not expose a symbol tag.")
    return component_tag, symbol_tags[0]


def _resolve_symbol_text_tag(
    symbol_tag: Any,
    *,
    text_index: int | None,
    text_role: str | None,
    reference: str,
) -> tuple[int, Any]:
    """Resolve one symbol text selector to an index and raw tag."""

    if (text_index is None) == (text_role is None):
        raise ValueError("Provide exactly one of text_index or text_role.")
    text_tags = cast("list[Any]", symbol_tag.get_items("text"))
    if text_role is not None:
        normalized_role = text_role.strip().lower()
        if normalized_role == "reference":
            resolved_index = 0
        elif normalized_role == "value":
            resolved_index = 1
        else:
            raise ValueError("text_role must be either 'reference' or 'value'.")
    else:
        if text_index is None or text_index < 0:
            raise ValueError("text_index must be a non-negative integer.")
        resolved_index = text_index
    if resolved_index >= len(text_tags):
        raise ValueError(
            f"Component {reference} exposes {len(text_tags)} symbol text item(s); "
            f"cannot select index {resolved_index}."
        )
    return resolved_index, text_tags[resolved_index]


def _resolve_symbol_pin_tag(
    symbol_tag: Any,
    *,
    pin_index: int | None,
    pin_name: str | None,
    reference: str,
) -> tuple[int, Any]:
    """Resolve one symbol pin selector to an index and raw tag."""

    if (pin_index is None) == (pin_name is None):
        raise ValueError("Provide exactly one of pin_index or pin_name.")
    pin_tags = cast("list[Any]", symbol_tag.get_items("pin"))
    if pin_index is not None:
        if pin_index < 0 or pin_index >= len(pin_tags):
            raise ValueError(
                f"Component {reference} exposes {len(pin_tags)} symbol pin(s); "
                f"cannot select index {pin_index}."
            )
        return pin_index, pin_tags[pin_index]

    normalized_pin_name = _normalize_pin_name(cast("str", pin_name))
    available_names: list[str] = []
    for index, pin_tag in enumerate(pin_tags):
        candidate_name = str(pin_tag.get_attr(8))
        available_names.append(candidate_name)
        if candidate_name == normalized_pin_name:
            return index, pin_tag
    raise ValueError(
        f"Component {reference} has no symbol pin named {normalized_pin_name}. "
        f"Available pins: {', '.join(sorted(available_names))}"
    )


def _read_symbol_metadata_attr(symbol_tag: Any, tag_name: str) -> str | None:
    """Read one simple metadata child tag from a symbol tag."""

    tag_items = symbol_tag.get_items(tag_name)
    if not tag_items:
        return None
    if len(tag_items[0].tokens) <= 1:
        return None
    return str(tag_items[0].get_attr(1))


def _parse_qsch_point_token(token: object) -> tuple[int, int] | None:
    """Parse one QSch point token when it matches the standard `(x,y)` form."""

    normalized = str(token).strip()
    if not normalized.startswith("(") or not normalized.endswith(")"):
        return None
    x_token, separator, y_token = normalized[1:-1].partition(",")
    if separator != ",":
        return None
    try:
        return int(x_token), int(y_token)
    except ValueError:
        return None


def _symbol_item_image_asset_tokens(item: Any) -> tuple[str, ...]:
    """Collect quoted image-like asset tokens referenced by one symbol child item."""

    image_tokens: list[str] = []
    for token in item.tokens[1:]:
        normalized = _unquote_qsch_string(str(token))
        if normalized.lower().endswith(_IMAGE_FILE_SUFFIXES):
            image_tokens.append(normalized)
    return tuple(image_tokens)


def _symbol_image_asset_tokens(symbol_tag: Any) -> tuple[str, ...]:
    """Collect quoted image-like asset tokens referenced by a symbol."""

    image_tokens: list[str] = []
    for item in cast("list[Any]", symbol_tag.items):
        image_tokens.extend(_symbol_item_image_asset_tokens(item))
    return tuple(image_tokens)


def _is_symbol_drawing_tag(item: Any) -> bool:
    """Return whether one symbol child item is a drawable layout tag."""

    tag_name = str(item.tag)
    return tag_name not in _SYMBOL_METADATA_TAGS and tag_name not in {"text", "pin"}


def _symbol_drawing_metadata(item: Any, *, index: int) -> SymbolDrawingMetadata:
    """Normalize one raw symbol drawing tag into a repo-owned metadata record."""

    arguments = tuple(str(token) for token in item.tokens[1:])
    coordinate_points = tuple(
        coordinate
        for token in item.tokens[1:]
        for coordinate in [_parse_qsch_point_token(token)]
        if coordinate is not None
    )
    return SymbolDrawingMetadata(
        index=index,
        tag_name=str(item.tag),
        arguments=arguments,
        coordinate_points=coordinate_points,
        image_asset_tokens=_symbol_item_image_asset_tokens(item),
    )


def _symbol_drawing_items(symbol_tag: Any) -> tuple[SymbolDrawingMetadata, ...]:
    """Return normalized drawing items from one symbol tag in display order."""

    drawing_index = 0
    drawing_items: list[SymbolDrawingMetadata] = []
    for item in cast("list[Any]", symbol_tag.items):
        if not _is_symbol_drawing_tag(item):
            continue
        drawing_items.append(_symbol_drawing_metadata(item, index=drawing_index))
        drawing_index += 1
    return tuple(drawing_items)


def _normalize_symbol_drawing_tag_name(tag_name: str) -> str:
    """Normalize one requested symbol drawing tag name."""

    normalized = tag_name.strip().lower()
    if not normalized:
        raise ValueError("tag_name must not be empty.")
    if normalized in _SYMBOL_METADATA_TAGS or normalized in {"text", "pin"}:
        raise ValueError(
            "tag_name must identify a symbol drawing item, not symbol metadata, text, or pin tags."
        )
    return normalized


def _normalize_symbol_drawing_arguments(arguments: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Normalize one requested symbol drawing argument sequence."""

    return tuple(str(argument).strip() for argument in arguments)


def _resolve_symbol_drawing_tag(
    symbol_tag: Any,
    *,
    drawing_index: int,
    reference: str,
) -> tuple[int, int, Any]:
    """Resolve one drawing selector to the raw symbol child item and item index."""

    drawing_item_indexes = [
        index
        for index, item in enumerate(cast("list[Any]", symbol_tag.items))
        if _is_symbol_drawing_tag(item)
    ]
    if drawing_index < 0 or drawing_index >= len(drawing_item_indexes):
        raise ValueError(
            f"Component {reference} exposes {len(drawing_item_indexes)} symbol drawing item(s); "
            f"cannot select index {drawing_index}."
        )
    item_index = drawing_item_indexes[drawing_index]
    return drawing_index, item_index, symbol_tag.items[item_index]


def _resolve_symbol_drawing_insert_position(
    symbol_tag: Any,
    *,
    insert_index: int | None,
    reference: str,
) -> tuple[int, int]:
    """Resolve one drawing insertion selector to a drawing index and raw item position."""

    drawing_item_indexes = [
        index
        for index, item in enumerate(cast("list[Any]", symbol_tag.items))
        if _is_symbol_drawing_tag(item)
    ]
    if insert_index is None:
        resolved_index = len(drawing_item_indexes)
    else:
        if insert_index < 0 or insert_index > len(drawing_item_indexes):
            raise ValueError(
                f"Component {reference} exposes "
                f"{len(drawing_item_indexes)} symbol drawing item(s); "
                f"cannot insert at index {insert_index}."
            )
        resolved_index = insert_index

    if resolved_index < len(drawing_item_indexes):
        return resolved_index, drawing_item_indexes[resolved_index]
    if drawing_item_indexes:
        return resolved_index, drawing_item_indexes[-1] + 1

    for item_index, item in enumerate(cast("list[Any]", symbol_tag.items)):
        if str(item.tag) in {"text", "pin"}:
            return resolved_index, item_index
    return resolved_index, len(cast("list[Any]", symbol_tag.items))


def read_component_symbol_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> ComponentSymbolMetadata:
    """Return normalized symbol metadata for one component instance."""

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)

    text_attributes = tuple(
        SymbolTextMetadata(
            index=index,
            role=_symbol_text_role(index),
            text=str(text_tag.get_attr(qsch_module.QSCH_TEXT_STR_ATTR)),
            position_x=normalize_component_position(text_tag.get_attr(qsch_module.QSCH_TEXT_POS))[
                0
            ],
            position_y=normalize_component_position(text_tag.get_attr(qsch_module.QSCH_TEXT_POS))[
                1
            ],
            size=int(text_tag.get_attr(qsch_module.QSCH_TEXT_SIZE)),
            rotation_code=int(text_tag.get_attr(qsch_module.QSCH_TEXT_ROTATION)),
            rotation_degrees=_symbol_rotation_degrees(
                int(text_tag.get_attr(qsch_module.QSCH_TEXT_ROTATION))
            ),
            is_comment=bool(int(text_tag.get_attr(qsch_module.QSCH_TEXT_COMMENT))),
            color_code=_normalize_qsch_color_code(text_tag.tokens[qsch_module.QSCH_TEXT_COLOR]),
        )
        for index, text_tag in enumerate(symbol_tag.get_items("text"))
    )

    pins = tuple(
        SymbolPinMetadata(
            index=index,
            name=str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET)),
            position_x=normalize_component_position(
                pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS1)
            )[0],
            position_y=normalize_component_position(
                pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS1)
            )[1],
            label_position_x=normalize_component_position(
                pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS2)
            )[0],
            label_position_y=normalize_component_position(
                pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_POS2)
            )[1],
            text_size=int(pin_tag.get_attr(_SYMBOL_PIN_TEXT_SIZE)),
            label_anchor_code=int(pin_tag.get_attr(_SYMBOL_PIN_LABEL_ANCHOR)),
            pin_kind_code=int(pin_tag.get_attr(_SYMBOL_PIN_KIND)),
            color_code=_normalize_qsch_color_code(pin_tag.tokens[_SYMBOL_PIN_COLOR]),
            aux_code=int(pin_tag.get_attr(_SYMBOL_PIN_AUX)),
            behavioral_net_override=(
                (behavioral_override if behavioral_override else None)
                if len(pin_tag.tokens) > qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL
                else None
            ),
        )
        for index, pin_tag in enumerate(symbol_tag.get_items("pin"))
        for behavioral_override in [
            str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL)).strip()
            if len(pin_tag.tokens) > qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL
            else ""
        ]
    )

    drawing_items = _symbol_drawing_items(symbol_tag)
    drawing_tags: list[str] = []
    for drawing_item in drawing_items:
        if drawing_item.tag_name not in drawing_tags:
            drawing_tags.append(drawing_item.tag_name)

    return ComponentSymbolMetadata(
        symbol_name=str(symbol_tag.tokens[1]) if len(symbol_tag.tokens) > 1 else "",
        type_name=_read_symbol_metadata_attr(symbol_tag, "type:"),
        description=_read_symbol_metadata_attr(symbol_tag, "description:"),
        library_file=_read_symbol_metadata_attr(symbol_tag, "library file:"),
        shorted_pins=_normalize_optional_bool(
            _read_symbol_metadata_attr(symbol_tag, "shorted pins:")
        ),
        text_attributes=text_attributes,
        pins=pins,
        drawing_items=drawing_items,
        drawing_tags=tuple(drawing_tags),
        image_asset_tokens=_symbol_image_asset_tokens(symbol_tag),
    )


def set_component_symbol_text_attributes(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    text_index: int | None = None,
    text_role: str | None = None,
    text: str | None = None,
    position: tuple[int, int] | None = None,
    size: int | None = None,
    rotation_code: int | None = None,
    is_comment: bool | None = None,
    color_code: str | int | None = None,
) -> SymbolTextMetadata:
    """Mutate one embedded symbol text item and return its normalized metadata."""

    if (
        text is None
        and position is None
        and size is None
        and rotation_code is None
        and is_comment is None
        and color_code is None
    ):
        raise ValueError("At least one symbol text attribute update must be provided.")

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    resolved_index, text_tag = _resolve_symbol_text_tag(
        symbol_tag,
        text_index=text_index,
        text_role=text_role,
        reference=reference,
    )

    if text is not None:
        if resolved_index == qsch_module.QSCH_SYMBOL_TEXT_REFDES:
            raise ValueError(
                "Changing the reference text content is not supported; "
                "use a dedicated rename flow instead."
            )
        if resolved_index == qsch_module.QSCH_SYMBOL_TEXT_VALUE:
            editor.set_component_value(reference, text)
        else:
            text_tag.set_attr(qsch_module.QSCH_TEXT_STR_ATTR, text)
    if position is not None:
        text_tag.set_attr(qsch_module.QSCH_TEXT_POS, position)
    if size is not None:
        text_tag.set_attr(qsch_module.QSCH_TEXT_SIZE, int(size))
    if rotation_code is not None:
        text_tag.set_attr(qsch_module.QSCH_TEXT_ROTATION, int(rotation_code))
    if is_comment is not None:
        text_tag.set_attr(qsch_module.QSCH_TEXT_COMMENT, 1 if is_comment else 0)
    if color_code is not None:
        text_tag.set_attr(qsch_module.QSCH_TEXT_COLOR, _coerce_qsch_color_code(color_code))

    editor.updated = True
    return read_component_symbol_metadata(editor, reference=reference).text_attributes[
        resolved_index
    ]


def _apply_symbol_pin_behavioral_override(
    pin_tag: Any,
    *,
    qsch_module: Any,
    behavioral_net_override: str | None,
    clear_behavioral_net_override: bool,
) -> None:
    """Apply or clear the optional behavioral net override on one symbol pin."""

    if behavioral_net_override is not None:
        normalized_override = _normalize_net_name(behavioral_net_override)
        if len(pin_tag.tokens) > qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL:
            pin_tag.set_attr(qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL, normalized_override)
        else:
            pin_tag.tokens.append(_quote_qsch_string(normalized_override))
        return

    if (
        clear_behavioral_net_override
        and len(pin_tag.tokens) > qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL
    ):
        pin_tag.tokens.pop(qsch_module.QSCH_SYMBOL_PIN_NET_BEHAVIORAL)


def set_component_symbol_pin_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    pin_index: int | None = None,
    pin_name: str | None = None,
    new_pin_name: str | None = None,
    label_position: tuple[int, int] | None = None,
    text_size: int | None = None,
    label_anchor_code: int | None = None,
    pin_kind_code: int | None = None,
    color_code: str | int | None = None,
    aux_code: int | None = None,
    behavioral_net_override: str | None = None,
    clear_behavioral_net_override: bool = False,
) -> SymbolPinMetadata:
    """Mutate one embedded symbol pin item and return its normalized metadata."""

    if (
        new_pin_name is None
        and label_position is None
        and text_size is None
        and label_anchor_code is None
        and pin_kind_code is None
        and color_code is None
        and aux_code is None
        and behavioral_net_override is None
        and not clear_behavioral_net_override
    ):
        raise ValueError("At least one symbol pin attribute update must be provided.")
    if behavioral_net_override is not None and clear_behavioral_net_override:
        raise ValueError(
            "behavioral_net_override and clear_behavioral_net_override cannot be used together."
        )

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    resolved_index, pin_tag = _resolve_symbol_pin_tag(
        symbol_tag,
        pin_index=pin_index,
        pin_name=pin_name,
        reference=reference,
    )

    if new_pin_name is not None:
        pin_tag.set_attr(qsch_module.QSCH_SYMBOL_PIN_NET, _normalize_pin_name(new_pin_name))
    if label_position is not None:
        pin_tag.set_attr(qsch_module.QSCH_SYMBOL_PIN_POS2, label_position)
    if text_size is not None:
        pin_tag.set_attr(_SYMBOL_PIN_TEXT_SIZE, int(text_size))
    if label_anchor_code is not None:
        pin_tag.set_attr(_SYMBOL_PIN_LABEL_ANCHOR, int(label_anchor_code))
    if pin_kind_code is not None:
        pin_tag.set_attr(_SYMBOL_PIN_KIND, int(pin_kind_code))
    if color_code is not None:
        pin_tag.set_attr(_SYMBOL_PIN_COLOR, _coerce_qsch_color_code(color_code))
    if aux_code is not None:
        pin_tag.set_attr(_SYMBOL_PIN_AUX, int(aux_code))
    _apply_symbol_pin_behavioral_override(
        pin_tag,
        qsch_module=qsch_module,
        behavioral_net_override=behavioral_net_override,
        clear_behavioral_net_override=clear_behavioral_net_override,
    )

    editor.updated = True
    return read_component_symbol_metadata(editor, reference=reference).pins[resolved_index]


def add_component_symbol_drawing_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    tag_name: str,
    arguments: tuple[str, ...] | list[str],
    insert_index: int | None = None,
) -> SymbolDrawingMetadata:
    """Insert one embedded symbol drawing item and return its normalized metadata."""

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    resolved_index, item_index = _resolve_symbol_drawing_insert_position(
        symbol_tag,
        insert_index=insert_index,
        reference=reference,
    )
    symbol_tag.items.insert(
        item_index,
        qsch_module.QschTag(
            _normalize_symbol_drawing_tag_name(tag_name),
            *_normalize_symbol_drawing_arguments(arguments),
        ),
    )

    editor.updated = True
    return read_component_symbol_metadata(editor, reference=reference).drawing_items[resolved_index]


def set_component_symbol_drawing_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    drawing_index: int,
    tag_name: str | None = None,
    arguments: tuple[str, ...] | list[str] | None = None,
) -> SymbolDrawingMetadata:
    """Replace one embedded symbol drawing item and return its normalized metadata."""

    if tag_name is None and arguments is None:
        raise ValueError("At least one symbol drawing update must be provided.")

    qsch_module, _ = _load_qsch_support_modules()
    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    resolved_index, item_index, drawing_tag = _resolve_symbol_drawing_tag(
        symbol_tag,
        drawing_index=drawing_index,
        reference=reference,
    )
    replacement_tag_name = (
        str(drawing_tag.tag) if tag_name is None else _normalize_symbol_drawing_tag_name(tag_name)
    )
    replacement_arguments = (
        tuple(str(token) for token in drawing_tag.tokens[1:])
        if arguments is None
        else _normalize_symbol_drawing_arguments(arguments)
    )
    symbol_tag.items[item_index] = qsch_module.QschTag(
        replacement_tag_name,
        *replacement_arguments,
    )

    editor.updated = True
    return read_component_symbol_metadata(editor, reference=reference).drawing_items[resolved_index]


def remove_component_symbol_drawing_metadata(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    drawing_index: int,
) -> SymbolDrawingMetadata:
    """Remove one embedded symbol drawing item and return the removed metadata."""

    _, symbol_tag = _component_symbol_tag(editor, reference=reference)
    resolved_index, item_index, drawing_tag = _resolve_symbol_drawing_tag(
        symbol_tag,
        drawing_index=drawing_index,
        reference=reference,
    )
    removed = _symbol_drawing_metadata(drawing_tag, index=resolved_index)
    symbol_tag.items.pop(item_index)
    editor.updated = True
    return removed


def _append_schematic_tag(editor: _QschEditorProtocol, tag: object) -> None:
    """Append one raw QSch tag to the root schematic tree (idempotent)."""

    bootstrap_blank_schematic(editor)
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    if tag in items:
        return  # avoid double-append when add_component already registered it
    items.append(tag)
    editor.updated = True


def _build_two_pin_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    reference_prefix: str,
    symbol_name: str,
    type_name: str,
    description: str,
    default_value: str,
    drawing_defs: tuple[tuple[object, ...], ...],
    pin_defs: tuple[tuple[object, ...], ...],
    port_names: tuple[str, str],
    refdes_text_position: str = "(100,150)",
    value_text_position: str = "(100,-150)",
    library_file: str | None = None,
) -> _SchematicComponentProtocol:
    """Create one two-pin schematic component object ready for insertion."""

    if not reference.upper().startswith(reference_prefix):
        raise ValueError(f"{symbol_name} references must start with '{reference_prefix}'.")

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    tag_class = qsch_module.QschTag
    component = base_schematic_module.SchematicComponent(editor, reference)
    component_tag = tag_class("component", "(0,0)", 0, 0)
    symbol_tag = tag_class("symbol", symbol_name)
    symbol_tag.items.append(tag_class("type:", type_name))
    symbol_tag.items.append(tag_class("description:", description))
    if library_file is not None:
        symbol_tag.items.append(tag_class("library file:", library_file))
    symbol_tag.items.append(tag_class("shorted pins:", "false"))
    for item_def in drawing_defs:
        symbol_tag.items.append(tag_class(*item_def))
    symbol_tag.items.append(
        tag_class("text", refdes_text_position, 1, 7, 0, "0x1000000", -1, -1, '""')
    )
    symbol_tag.items.append(
        tag_class("text", value_text_position, 1, 7, 0, "0x1000000", -1, -1, '""')
    )
    for item_def in pin_defs:
        symbol_tag.items.append(tag_class(*item_def))
    component_tag.items.append(symbol_tag)

    texts = symbol_tag.get_items("text")
    texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(qsch_module.QSCH_TEXT_STR_ATTR, reference)
    texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].set_attr(
        qsch_module.QSCH_TEXT_STR_ATTR, default_value
    )

    component.reference = reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    component.attributes["type"] = type_name
    component.attributes["description"] = description
    if library_file is not None:
        component.attributes["library file"] = library_file
    component.attributes["value"] = default_value
    component.attributes["tag"] = component_tag
    component.attributes["enabled"] = True
    component.ports = list(port_names)
    return cast("_SchematicComponentProtocol", component)


def _build_resistor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one resistor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_RESISTOR_REFERENCE_PREFIX,
        symbol_name="R",
        type_name="R",
        description="Resistor(USA Style Symbol)",
        default_value="1",
        drawing_defs=(
            ("line", "(0,200)", "(0,180)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-180)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            (
                "zigzag",
                "(-80,180)",
                "(80,-180)",
                0,
                0,
                0,
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"1"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"2"'),
        ),
        port_names=("1", "2"),
    )


def _build_capacitor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one capacitor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_CAPACITOR_REFERENCE_PREFIX,
        symbol_name="C",
        type_name="C",
        description="Capacitor",
        default_value="1u",
        drawing_defs=(
            ("line", "(0,200)", "(0,40)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-40)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            (
                "rect",
                "(-130,-40)",
                "(130,-30)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-130,30)",
                "(130,40)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
    )


def _build_diode_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one diode component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_DIODE_REFERENCE_PREFIX,
        symbol_name="D",
        type_name="D",
        description="Silicon Diode",
        default_value="D",
        drawing_defs=(
            ("line", "(100,80)", "(-100,80)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,80)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-200)", "(0,-70)", 0, 0, "0x1000000", -1, -1),
            (
                "triangle",
                "(0,80)",
                "(100,-70)",
                "(-100,-70)",
                0,
                0,
                "0x1000000",
                "0x2000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"A"'),
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"K"'),
        ),
        port_names=("A", "K"),
        refdes_text_position="(100,200)",
        value_text_position="(100,-200)",
        library_file="Diode.txt",
    )


def _build_voltage_source_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one independent voltage source component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_VOLTAGE_SOURCE_REFERENCE_PREFIX,
        symbol_name="V",
        type_name="V",
        description="Independent Voltage Source",
        default_value="1",
        drawing_defs=(
            ("line", "(0,-130)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,130)", 0, 0, "0x1000000", -1, -1),
            (
                "rect",
                "(-25,77)",
                "(25,73)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-2,50)",
                "(2,100)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-25,-73)",
                "(25,-77)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "ellipse",
                "(-130,130)",
                "(130,-130)",
                0,
                0,
                0,
                "0x1000000",
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
        value_text_position="(0,380)",
    )


def _build_inductor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one inductor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_INDUCTOR_REFERENCE_PREFIX,
        symbol_name="L",
        type_name="L",
        description="Inductor",
        default_value="1u",
        drawing_defs=(
            ("line", "(0,200)", "(0,180)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-200)", "(0,-180)", 0, 0, "0x1000000", -1, -1),
            ("coil", "(-80,180)", "(80,-180)", 0, 0, 0, "0x1000000", -1, -1),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"1"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"2"'),
        ),
        port_names=("1", "2"),
        refdes_text_position="(80,0)",
        value_text_position="(-80,0)",
    )


def _build_behavioral_source_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one behavioral voltage source component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_BEHAVIORAL_REFERENCE_PREFIX,
        symbol_name="B",
        type_name="B",
        description="Behavioral Voltage Source",
        default_value="V=0",
        drawing_defs=(
            ("line", "(0,-130)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,130)", 0, 0, "0x1000000", -1, -1),
            ("rect", "(-25,77)", "(25,73)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            ("rect", "(-2,50)", "(2,100)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            ("rect", "(-25,-73)", "(25,-77)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            (
                "ellipse",
                "(-130,130)",
                "(130,-130)",
                0,
                0,
                0,
                "0x1000000",
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
        refdes_text_position="(130,0)",
        value_text_position="(-130,0)",
    )


def _build_mosfet_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    polarity: Literal["nmos", "pmos"],
) -> _SchematicComponentProtocol:
    """Create one library-backed MOSFET component object ready for insertion."""

    if not reference.upper().startswith(_MOSFET_REFERENCE_PREFIX):
        raise ValueError(f"MOSFET references must start with '{_MOSFET_REFERENCE_PREFIX}'.")

    if polarity == "nmos":
        symbol_name = "NMOS"
        type_name = "MN"
        description = "N-Channel MOSFET Transistor"
        library_file = "NMOS.txt"
        default_value = "NMOS"
        channel_triangle = (
            "triangle",
            "(70,-150)",
            "(-25,-125)",
            "(-25,-175)",
            0,
            0,
            "0x1000000",
            "0x3000000",
            -1,
            -1,
        )
    else:
        symbol_name = "PMOS"
        type_name = "MP"
        description = "P-Channel MOSFET Transistor"
        library_file = "PMOS.txt"
        default_value = "PMOS"
        channel_triangle = (
            "triangle",
            "(-25,-125)",
            "(70,-150)",
            "(70,-175)",
            0,
            0,
            "0x1000000",
            "0x3000000",
            -1,
            -1,
        )

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    tag_class = qsch_module.QschTag
    component = base_schematic_module.SchematicComponent(editor, reference)
    component_tag = tag_class("component", "(0,0)", 0, 0)
    symbol_tag = tag_class("symbol", symbol_name)
    symbol_tag.items.append(tag_class("type:", type_name))
    symbol_tag.items.append(tag_class("description:", description))
    symbol_tag.items.append(tag_class("library file:", library_file))
    symbol_tag.items.append(tag_class("shorted pins:", "false"))
    for item_def in (
        ("line", "(100,200)", "(100,150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,-150)", "(100,-200)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-100,150)", "(-100,-150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-100,0)", "(-200,0)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,-150)", "(-50,-150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,150)", "(-50,150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-50,150)", "(-50,-150)", 0, 0, "0x1000000", -1, -1),
        channel_triangle,
    ):
        symbol_tag.items.append(tag_class(*item_def))
    symbol_tag.items.append(tag_class("text", "(100,-200)", 1, 102, 0, "0x1000000", -1, -1, '""'))
    symbol_tag.items.append(tag_class("text", "(-200,1200)", 1, 103, 0, "0x1000000", -1, -1, '""'))
    for pin_def in (
        ("pin", "(100,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"D"'),
        ("pin", "(-200,0)", "(0,0)", 1, 0, 0, "0x0", -1, '"G"'),
        ("pin", "(100,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"S"'),
    ):
        symbol_tag.items.append(tag_class(*pin_def))
    component_tag.items.append(symbol_tag)

    texts = symbol_tag.get_items("text")
    texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(qsch_module.QSCH_TEXT_STR_ATTR, reference)
    texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].set_attr(
        qsch_module.QSCH_TEXT_STR_ATTR, default_value
    )

    component.reference = reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    component.attributes["type"] = type_name
    component.attributes["description"] = description
    component.attributes["library file"] = library_file
    component.attributes["value"] = default_value
    component.attributes["tag"] = component_tag
    component.attributes["enabled"] = True
    component.ports = ["D", "G", "S"]
    return cast("_SchematicComponentProtocol", component)


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


def bootstrap_blank_schematic(editor: _QschEditorProtocol) -> None:
    """Attach a minimal root tag to an editor created with `create_blank=True`."""

    if editor.schematic is not None:
        return
    qsch_module, _ = _load_qsch_support_modules()
    editor.schematic = qsch_module.QschTag("schematic")
    editor.updated = True


def add_net_label(
    editor: _QschEditorProtocol,
    *,
    net_name: str,
    position: tuple[int, int],
) -> str:
    """Add one net label to the current editor and return its normalized name."""

    normalized_net_name = _normalize_net_name(net_name)
    qsch_module, _ = _load_qsch_support_modules()
    style = (
        _NET_LABEL_STYLE_GROUND
        if normalized_net_name.upper() in {_GROUND_NET_NAME, "0"}
        else _NET_LABEL_STYLE_DEFAULT
    )
    label_tag = qsch_module.QschTag(
        "net",
        _format_qsch_point(position),
        _NET_LABEL_KIND,
        style,
        _NET_LABEL_FLAGS,
        _quote_qsch_string(normalized_net_name),
    )
    _append_schematic_tag(editor, label_tag)
    return normalized_net_name


def add_junction(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
) -> tuple[int, int]:
    """Add one junction node to the current editor."""

    bootstrap_blank_schematic(editor)
    qsch_module, _ = _load_qsch_support_modules()
    junction_tag = qsch_module.QschTag("junction", _format_qsch_point(position))
    _append_schematic_tag(editor, junction_tag)
    return position


def add_wire(
    editor: _QschEditorProtocol,
    *,
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
    net_name: str,
) -> str:
    """Add one wire segment to the current editor and return its normalized net name."""

    start_position, end_position = resolve_wire_points(
        editor,
        start=start,
        end=end,
        start_reference=start_reference,
        start_pin=start_pin,
        end_reference=end_reference,
        end_pin=end_pin,
    )
    normalized_net_name = _normalize_net_name(net_name)
    qsch_module, _ = _load_qsch_support_modules()
    wire_tag = qsch_module.QschTag(
        "wire",
        _format_qsch_point(start_position),
        _format_qsch_point(end_position),
        _quote_qsch_string(normalized_net_name),
    )
    _append_schematic_tag(editor, wire_tag)
    return normalized_net_name


_QSCH_POINT_PATTERN = re.compile(r"^\((-?\d+),(-?\d+)\)$")


def _parse_qsch_point(token: str) -> tuple[int, int]:
    match = _QSCH_POINT_PATTERN.match(str(token).strip())
    if match is None:
        raise ValueError(f"Invalid QSch point token: {token!r}")
    return int(match.group(1)), int(match.group(2))


def _wire_endpoints_match(
    first: tuple[int, int],
    second: tuple[int, int],
    *,
    target_start: tuple[int, int],
    target_end: tuple[int, int],
) -> bool:
    forward = first == target_start and second == target_end
    reverse = first == target_end and second == target_start
    return forward or reverse


def remove_wire(
    editor: _QschEditorProtocol,
    *,
    start: tuple[int, int] | None = None,
    end: tuple[int, int] | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
    net_name: str | None = None,
) -> str:
    """Remove one wire segment matching the resolved endpoints and optional net name."""

    start_position, end_position = resolve_wire_points(
        editor,
        start=start,
        end=end,
        start_reference=start_reference,
        start_pin=start_pin,
        end_reference=end_reference,
        end_pin=end_pin,
    )
    normalized_net_name = _normalize_net_name(net_name) if net_name is not None else None
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "wire":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 3:  # noqa: PLR2004
            continue
        wire_start = _parse_qsch_point(str(tokens[1]))
        wire_end = _parse_qsch_point(str(tokens[2]))
        wire_net = _unquote_qsch_string(str(tokens[3])) if len(tokens) >= 4 else None  # noqa: PLR2004
        if normalized_net_name is not None and wire_net != normalized_net_name:
            continue
        if not _wire_endpoints_match(
            wire_start,
            wire_end,
            target_start=start_position,
            target_end=end_position,
        ):
            continue
        items.pop(index)
        editor.updated = True
        return wire_net or normalized_net_name or ""
    raise QSpiceError("No matching wire segment was found for the requested endpoints.")


def remove_net_label(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
    net_name: str | None = None,
) -> str:
    """Remove one net label at the given position and optional net name."""

    normalized_net_name = _normalize_net_name(net_name) if net_name is not None else None
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "net":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 6:  # noqa: PLR2004
            continue
        label_position = _parse_qsch_point(str(tokens[1]))
        if label_position != position:
            continue
        label_net = _unquote_qsch_string(str(tokens[5]))
        if normalized_net_name is not None and label_net != normalized_net_name:
            continue
        items.pop(index)
        editor.updated = True
        return label_net or normalized_net_name or ""
    raise QSpiceError("No matching net label was found for the requested position.")


def remove_junction(
    editor: _QschEditorProtocol,
    *,
    position: tuple[int, int],
) -> tuple[int, int]:
    """Remove one junction node at the given position."""

    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    for index, tag in enumerate(list(items)):
        if getattr(tag, "tag", None) != "junction":
            continue
        tokens = list(getattr(tag, "tokens", ()))
        if len(tokens) < 2:  # noqa: PLR2004
            continue
        junction_position = _parse_qsch_point(str(tokens[1]))
        if junction_position != position:
            continue
        items.pop(index)
        editor.updated = True
        return junction_position
    raise QSpiceError("No matching junction was found for the requested position.")


def create_blank_schematic_file(
    output_path: str | Path,
    *,
    workspace_root: Path,
    overwrite: bool = False,
) -> tuple[Path, bool]:
    """Create a minimal blank `.qsch` file inside the workspace root."""

    destination = resolve_schematic_output_path(
        output_path,
        workspace_root=workspace_root.resolve(strict=False),
        default=workspace_root / "untitled.qsch",
    )
    existed = destination.exists()
    if existed and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing schematic: {destination}")

    editor_factory, backend_name = load_qsch_editor_factory()
    if editor_factory is None or backend_name is None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_blank_schematic(destination)
        return destination.resolve(strict=False), existed

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        editor = editor_factory(str(destination), create_blank=True)
    except Exception as exc:
        raise QSpiceError(
            f"Failed to create a blank schematic at {destination.name} "
            f"using {backend_name}.QschEditor."
        ) from exc

    bootstrap_blank_schematic(editor)
    editor.save_as(destination)
    if not destination.is_file():
        raise ArtifactMissingError(
            f"Blank schematic creation did not produce an artifact: {destination}"
        )
    return destination.resolve(strict=False), existed


def _build_simple_component(
    editor: _QschEditorProtocol,
    normalized_kind: str,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Construct the component object for one normalized simple-component kind."""

    builders: dict[str, Callable[[], _SchematicComponentProtocol]] = {
        "resistor": lambda: _build_resistor_component(editor, reference=reference),
        "capacitor": lambda: _build_capacitor_component(editor, reference=reference),
        "diode": lambda: _build_diode_component(editor, reference=reference),
        "voltage_source": lambda: _build_voltage_source_component(editor, reference=reference),
        "inductor": lambda: _build_inductor_component(editor, reference=reference),
        "behavioral": lambda: _build_behavioral_source_component(editor, reference=reference),
        "nmos": lambda: _build_mosfet_component(editor, reference=reference, polarity="nmos"),
        "pmos": lambda: _build_mosfet_component(editor, reference=reference, polarity="pmos"),
    }
    builder = builders.get(normalized_kind)
    if builder is None:
        raise AssertionError(f"Unhandled component kind: {normalized_kind}")
    return builder()


def add_simple_component(
    editor: _QschEditorProtocol,
    *,
    component_kind: str,
    reference: str | None,
    value: str | int | float | complex | None,
    position: tuple[int, int],
    rotation_degrees: int = 0,
    net_name: str | None = None,
) -> SimpleComponentKind:
    """Add one supported simple component to the current editor."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    normalized_kind = _normalize_component_kind(component_kind)
    bootstrap_blank_schematic(editor)

    if normalized_kind == "ground":
        add_net_label(
            editor,
            net_name=net_name or _GROUND_NET_NAME,
            position=position,
        )
        return normalized_kind

    if reference is None or not reference.strip():
        raise ValueError(f"{normalized_kind} components require a non-empty reference.")
    if value is None:
        raise ValueError(f"{normalized_kind} components require a value.")

    existing_references = {str(item) for item in editor.get_components(prefixes="*")}
    if reference in existing_references:
        raise ValueError(f"Component reference already exists in schematic: {reference}")

    component = _build_simple_component(editor, normalized_kind, reference=reference)

    editor.add_component(component)
    _append_schematic_tag(editor, component.attributes["tag"])
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(reference, position, rotation_index)
    editor.set_component_value(reference, value)
    editor.updated = True
    return normalized_kind


def add_dll_block(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    device_name: str,
    input_pin_names: tuple[str, ...] | list[str],
    output_pin_names: tuple[str, ...] | list[str],
    position: tuple[int, int],
    rotation_degrees: int = 0,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Add one `.DLL` custom-device block to the current editor."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    bootstrap_blank_schematic(editor)

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError(".DLL blocks require a non-empty reference.")

    normalized_input_pin_names = _normalize_dll_pin_names(input_pin_names)
    normalized_output_pin_names = _normalize_dll_pin_names(output_pin_names)

    existing_references = {str(item) for item in editor.get_components(prefixes="*")}
    if normalized_reference in existing_references:
        raise ValueError(f"Component reference already exists in schematic: {normalized_reference}")

    component = _build_dll_block_component(
        editor,
        reference=normalized_reference,
        device_name=device_name,
        input_pin_names=normalized_input_pin_names,
        output_pin_names=normalized_output_pin_names,
    )

    editor.add_component(component)
    _append_schematic_tag(editor, component.attributes["tag"])
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(normalized_reference, position, rotation_index)
    editor.set_component_value(normalized_reference, device_name)
    editor.updated = True
    return normalized_input_pin_names, normalized_output_pin_names


def set_component_rotation(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    rotation_degrees: int,
) -> int:
    """Rotate one placed component without changing its position."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")

    position, _rotation = editor.get_component_position(normalized_reference)
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(normalized_reference, position, rotation_index)
    editor.updated = True
    return rotation_degrees


def set_component_position(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    position_x: int,
    position_y: int,
    rotation_degrees: int | None = None,
) -> tuple[int, int, int]:
    """Move one placed component and optionally update its rotation."""

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")

    _position, rotation_index_raw = editor.get_component_position(normalized_reference)
    if not isinstance(rotation_index_raw, int):
        raise TypeError(f"Unsupported component rotation index: {rotation_index_raw!r}")
    rotation_index = rotation_index_raw
    if rotation_degrees is not None:
        if rotation_degrees % 45 != 0:
            raise ValueError("rotation_degrees must be a multiple of 45.")
        rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    else:
        rotation_degrees = component_rotation_index_to_degrees(rotation_index)

    editor.set_component_position(
        normalized_reference,
        (int(position_x), int(position_y)),
        rotation_index,
    )
    editor.updated = True
    return int(position_x), int(position_y), rotation_degrees


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
    if (
        component_rotation_degrees == 0
        and rotation_code == FACTORY_SYMBOL_TEXT_ROTATION_CODE
        and target_rotation_code == symbol_text_rotation_code_for_degrees(0)
    ):
        return True
    return False


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
