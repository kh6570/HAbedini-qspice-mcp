"""Service for updating one component symbol drawing item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolDrawingMetadata,
    open_schematic_editor,
    set_component_symbol_drawing_metadata,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolDrawingUpdate:
    """Metadata for one updated embedded symbol drawing item."""

    schematic_path: Path
    output_path: Path
    reference: str
    drawing_item: SymbolDrawingMetadata


SERVICE_SPEC = ServiceSpec(
    name="set_component_symbol_drawing",
    title="Set Component Symbol Drawing",
    summary="Update one embedded symbol drawing item by replacing its tag or arguments.",
    phase="implemented",
    read_only=False,
)


def set_component_symbol_drawing(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    drawing_index: int,
    tag_name: str | None = None,
    arguments: tuple[str, ...] | list[str] | None = None,
    output_path: str | Path | None = None,
) -> ComponentSymbolDrawingUpdate:
    """Update one embedded symbol drawing item and persist the edited schematic."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    drawing_item = set_component_symbol_drawing_metadata(
        editor,
        reference=reference,
        drawing_index=drawing_index,
        tag_name=tag_name,
        arguments=arguments,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return ComponentSymbolDrawingUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        drawing_item=drawing_item,
    )


__all__ = [
    "SERVICE_SPEC",
    "ComponentSymbolDrawingUpdate",
    "set_component_symbol_drawing",
]
