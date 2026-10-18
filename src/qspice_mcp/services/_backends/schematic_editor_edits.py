"""Facade for schematic edit operations.

Implementations live in ``schematic_edits`` so this module stays an import surface.
"""

from __future__ import annotations

from .schematic_edits.dll_block import (
    add_dll_block_pin_metadata,
    remove_dll_block_pin_metadata,
    set_dll_block_pin_role_metadata,
)
from .schematic_edits.library import (
    ClonedLibraryComponent,
    add_qsym_symbol_component,
    clone_library_component,
    export_component_symbol_tag,
)
from .schematic_edits.placement import (
    FACTORY_SYMBOL_TEXT_ROTATION_CODE,
    UPRIGHT_SYMBOL_TEXT_ROTATION_CODE,
    NormalizedSymbolTextRotation,
    WireFollowMove,
    move_component_preserving_connections,
    normalize_component_symbol_text_rotation,
    symbol_text_rotation_code_for_degrees,
)
from .schematic_edits.primitives import (
    add_dll_block,
    add_simple_component,
    set_component_position,
    set_component_rotation,
)
from .schematic_edits.structure import (
    bootstrap_blank_schematic,
)
from .schematic_edits.symbol_metadata import (
    _component_symbol_tag,
    add_component_symbol_drawing_metadata,
    read_component_symbol_metadata,
    remove_component_symbol_drawing_metadata,
    set_component_symbol_drawing_metadata,
    set_component_symbol_pin_metadata,
    set_component_symbol_text_attributes,
)
from .schematic_edits.wiring import (
    OrphanConnectionCleanup,
    add_junction,
    add_net_label,
    add_wire,
    collect_component_pin_coordinates,
    create_blank_schematic_file,
    remove_component_with_orphan_cleanup,
    remove_junction,
    remove_net_label,
    remove_wire,
)

__all__ = [
    "FACTORY_SYMBOL_TEXT_ROTATION_CODE",
    "UPRIGHT_SYMBOL_TEXT_ROTATION_CODE",
    "ClonedLibraryComponent",
    "NormalizedSymbolTextRotation",
    "OrphanConnectionCleanup",
    "WireFollowMove",
    "_component_symbol_tag",
    "add_component_symbol_drawing_metadata",
    "add_dll_block",
    "add_dll_block_pin_metadata",
    "add_junction",
    "add_net_label",
    "add_qsym_symbol_component",
    "add_simple_component",
    "add_wire",
    "bootstrap_blank_schematic",
    "clone_library_component",
    "collect_component_pin_coordinates",
    "create_blank_schematic_file",
    "export_component_symbol_tag",
    "move_component_preserving_connections",
    "normalize_component_symbol_text_rotation",
    "read_component_symbol_metadata",
    "remove_component_symbol_drawing_metadata",
    "remove_component_with_orphan_cleanup",
    "remove_dll_block_pin_metadata",
    "remove_junction",
    "remove_net_label",
    "remove_wire",
    "set_component_position",
    "set_component_rotation",
    "set_component_symbol_drawing_metadata",
    "set_component_symbol_pin_metadata",
    "set_component_symbol_text_attributes",
    "set_dll_block_pin_role_metadata",
    "symbol_text_rotation_code_for_degrees",
]
