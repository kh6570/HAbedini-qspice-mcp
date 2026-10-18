# In the name of God, the Most Gracious, the Most Merciful
"""Schematic edit helpers: symbol metadata."""

from __future__ import annotations

from typing import Any, cast

from qspice_mcp.core.exceptions import QSpiceError

from ..schematic_editor_backend import (
    _IMAGE_FILE_SUFFIXES,
    _SYMBOL_METADATA_TAGS,
    _SYMBOL_PIN_AUX,
    _SYMBOL_PIN_COLOR,
    _SYMBOL_PIN_KIND,
    _SYMBOL_PIN_LABEL_ANCHOR,
    _SYMBOL_PIN_TEXT_SIZE,
    ComponentSymbolMetadata,
    SymbolDrawingMetadata,
    SymbolPinMetadata,
    SymbolTextMetadata,
    _coerce_qsch_color_code,
    _load_qsch_support_modules,
    _normalize_net_name,
    _normalize_optional_bool,
    _normalize_pin_name,
    _normalize_qsch_color_code,
    _QschEditorProtocol,
    _quote_qsch_string,
    _unquote_qsch_string,
    normalize_component_position,
)


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
    tokens = tag_items[0].tokens
    if len(tokens) <= 1:
        return None
    # Unquoted metadata such as «description: Resistor(USA Style Symbol)»
    # is split on spaces by the tokenizer. Rejoin every value token.
    parts = [str(tag_items[0].get_attr(index)) for index in range(1, len(tokens))]
    text = " ".join(part for part in parts if part).strip()
    return text or None


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
