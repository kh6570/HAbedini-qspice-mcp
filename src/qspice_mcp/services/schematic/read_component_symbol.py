"""Service for reading one component's embedded symbol metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolDrawingMetadata,
    SymbolPinMetadata,
    SymbolTextMetadata,
    open_schematic_editor,
    read_component_symbol_metadata,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolRead:
    """Normalized view of one component's embedded symbol metadata."""

    schematic_path: Path
    reference: str
    symbol_name: str
    type_name: str | None
    description: str | None
    library_file: str | None
    shorted_pins: bool | None
    text_attributes: tuple[SymbolTextMetadata, ...]
    pins: tuple[SymbolPinMetadata, ...]
    drawing_items: tuple[SymbolDrawingMetadata, ...]
    drawing_tags: tuple[str, ...]
    image_asset_tokens: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="read_component_symbol",
    title="Read Component Symbol",
    summary="Return embedded symbol text, pin, and drawing metadata for one schematic component.",
    phase="implemented",
)


def read_component_symbol(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
) -> ComponentSymbolRead:
    """Read one component's embedded symbol metadata through an installed editor backend."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    metadata = read_component_symbol_metadata(editor, reference=reference)
    return ComponentSymbolRead(
        schematic_path=resolved_path,
        reference=reference,
        symbol_name=metadata.symbol_name,
        type_name=metadata.type_name,
        description=metadata.description,
        library_file=metadata.library_file,
        shorted_pins=metadata.shorted_pins,
        text_attributes=metadata.text_attributes,
        pins=metadata.pins,
        drawing_items=metadata.drawing_items,
        drawing_tags=metadata.drawing_tags,
        image_asset_tokens=metadata.image_asset_tokens,
    )


__all__ = ["SERVICE_SPEC", "ComponentSymbolRead", "read_component_symbol"]
