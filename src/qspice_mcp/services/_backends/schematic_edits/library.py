# In the name of God, the Most Gracious, the Most Merciful
"""Schematic edit helpers: library."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, cast

from qspice_mcp.core.exceptions import QSpiceError

from ..schematic_editor_backend import (
    _load_qsch_support_modules,
    _QschEditorProtocol,
    _SchematicComponentProtocol,
    component_rotation_degrees_to_index,
)
from .structure import _append_schematic_tag, bootstrap_blank_schematic
from .symbol_metadata import _component_symbol_tag, _read_symbol_metadata_attr


@dataclass(frozen=True, slots=True)
class ClonedLibraryComponent:
    """Result of cloning one component symbol from a template schematic."""

    reference: str
    symbol_name: str
    type_name: str | None
    library_file: str | None
    value: str | None
    pin_names: tuple[str, ...]


def clone_library_component(  # noqa: PLR0915
    editor: _QschEditorProtocol,
    *,
    template_component_tag: Any,
    reference: str,
    position: tuple[int, int],
    value: str | None = None,
    rotation_degrees: int = 0,
) -> ClonedLibraryComponent:
    """Clone one component symbol subtree from a template into the current editor."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")
    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")
    if template_component_tag is None:
        raise QSpiceError("Template component does not expose a raw tag tree.")

    bootstrap_blank_schematic(editor)
    existing_references = {str(item) for item in editor.get_components(prefixes="*")}
    if normalized_reference in existing_references:
        raise ValueError(f"Component reference already exists in schematic: {normalized_reference}")

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    cloned_tag = copy.deepcopy(template_component_tag)
    symbol_tags = cloned_tag.get_items("symbol")
    if not symbol_tags:
        raise QSpiceError("Template component does not expose a symbol tag.")
    symbol_tag = symbol_tags[0]

    pin_names = tuple(
        str(pin_tag.get_attr(qsch_module.QSCH_SYMBOL_PIN_NET))
        for pin_tag in symbol_tag.get_items("pin")
    )
    if not pin_names:
        raise QSpiceError("Template component does not expose any pins.")

    symbol_name = str(symbol_tag.tokens[1]) if len(symbol_tag.tokens) > 1 else ""
    type_name = _read_symbol_metadata_attr(symbol_tag, "type:")
    library_file = _read_symbol_metadata_attr(symbol_tag, "library file:")

    texts = symbol_tag.get_items("text")
    if len(texts) > qsch_module.QSCH_SYMBOL_TEXT_REFDES:
        texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(
            qsch_module.QSCH_TEXT_STR_ATTR, normalized_reference
        )
    template_value: str | None = None
    if len(texts) > qsch_module.QSCH_SYMBOL_TEXT_VALUE:
        template_value = str(
            texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].get_attr(qsch_module.QSCH_TEXT_STR_ATTR)
        )
    resolved_value = value if value is not None else template_value

    component = base_schematic_module.SchematicComponent(editor, normalized_reference)
    component.reference = normalized_reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    if type_name is not None:
        component.attributes["type"] = type_name
    if library_file is not None:
        component.attributes["library file"] = library_file
    if resolved_value is not None:
        component.attributes["value"] = resolved_value
    component.attributes["tag"] = cloned_tag
    component.attributes["enabled"] = True
    component.ports = list(pin_names)

    editor.add_component(cast("_SchematicComponentProtocol", component))
    _append_schematic_tag(editor, cloned_tag)
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(normalized_reference, position, rotation_index)
    if resolved_value is not None:
        editor.set_component_value(normalized_reference, resolved_value)
    editor.updated = True

    return ClonedLibraryComponent(
        reference=normalized_reference,
        symbol_name=symbol_name,
        type_name=type_name,
        library_file=library_file,
        value=resolved_value,
        pin_names=pin_names,
    )


def export_component_symbol_tag(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    symbol_name: str | None = None,
) -> tuple[Any, str]:
    """Deep-copy one embedded component symbol tag for standalone `.qsym` export.

    Returns ``(symbol_tag, resolved_symbol_name)``.  The root tag is
    normalized to carry the symbol name token (``«symbol NAME ...»``) that
    standalone ``.qsym`` files require.
    """

    _component_tag, symbol_tag = _component_symbol_tag(editor, reference=reference)
    exported = copy.deepcopy(symbol_tag)

    resolved_name = (symbol_name or "").strip()
    if not resolved_name and len(exported.tokens) > 1:
        resolved_name = str(exported.tokens[1]).strip()
    if not resolved_name:
        resolved_name = str(editor.get_component_value(reference)).strip()
    if not resolved_name:
        resolved_name = reference.strip()
    # Symbol name tokens are whitespace-delimited on the wire.
    resolved_name = re.sub(r"\s+", "_", resolved_name)

    if len(exported.tokens) > 1:
        exported.tokens[1] = resolved_name
    else:
        exported.tokens.append(resolved_name)
    return exported, resolved_name


def add_qsym_symbol_component(
    editor: _QschEditorProtocol,
    *,
    symbol_tag: Any,
    reference: str,
    position: tuple[int, int],
    value: str | None = None,
    rotation_degrees: int = 0,
) -> ClonedLibraryComponent:
    """Insert one standalone `.qsym` symbol tag as a new schematic component."""

    if symbol_tag is None or getattr(symbol_tag, "tag", None) != "symbol":
        raise QSpiceError("Expected a parsed .qsym symbol tag.")

    qsch_module, _ = _load_qsch_support_modules()
    component_tag = qsch_module.QschTag("component", "(0,0)", "0", "0")
    component_tag.items.append(symbol_tag)
    return clone_library_component(
        editor,
        template_component_tag=component_tag,
        reference=reference,
        position=position,
        value=value,
        rotation_degrees=rotation_degrees,
    )
