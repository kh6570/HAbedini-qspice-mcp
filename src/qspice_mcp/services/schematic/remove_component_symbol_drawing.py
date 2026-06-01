"""Service for removing one component symbol drawing item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolDrawingMetadata,
    open_schematic_editor,
    remove_component_symbol_drawing_metadata,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolDrawingRemoval:
    """Metadata for one removed embedded symbol drawing item."""

    schematic_path: Path
    output_path: Path
    reference: str
    drawing_item: SymbolDrawingMetadata


SERVICE_SPEC = ServiceSpec(
    name="remove_component_symbol_drawing",
    title="Remove Component Symbol Drawing",
    summary="Remove one embedded symbol drawing item and persist the edited schematic.",
    phase="implemented",
    read_only=False,
)


def remove_component_symbol_drawing(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    drawing_index: int,
    output_path: str | Path | None = None,
) -> ComponentSymbolDrawingRemoval:
    """Remove one embedded symbol drawing item and persist the edited schematic."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    drawing_item = remove_component_symbol_drawing_metadata(
        editor,
        reference=reference,
        drawing_index=drawing_index,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return ComponentSymbolDrawingRemoval(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        drawing_item=drawing_item,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentSymbolDrawingRemoval",
    "remove_component_symbol_drawing",
]
