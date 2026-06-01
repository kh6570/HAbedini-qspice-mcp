"""Service for inserting one component symbol drawing item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolDrawingMetadata,
    add_component_symbol_drawing_metadata,
    open_schematic_editor,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolDrawingAdd:
    """Metadata for one inserted embedded symbol drawing item."""

    schematic_path: Path
    output_path: Path
    reference: str
    drawing_item: SymbolDrawingMetadata


SERVICE_SPEC = ServiceSpec(
    name="add_component_symbol_drawing",
    title="Add Component Symbol Drawing",
    summary="Insert one embedded symbol drawing item and persist the edited schematic.",
    phase="implemented",
    read_only=False,
)


def add_component_symbol_drawing(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    tag_name: str,
    arguments: tuple[str, ...] | list[str],
    insert_index: int | None = None,
    output_path: str | Path | None = None,
) -> ComponentSymbolDrawingAdd:
    """Insert one embedded symbol drawing item and persist the edited schematic."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    drawing_item = add_component_symbol_drawing_metadata(
        editor,
        reference=reference,
        tag_name=tag_name,
        arguments=arguments,
        insert_index=insert_index,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return ComponentSymbolDrawingAdd(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        drawing_item=drawing_item,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentSymbolDrawingAdd",
    "add_component_symbol_drawing",
]
