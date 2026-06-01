"""Service for updating one component symbol text item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolTextMetadata,
    open_schematic_editor,
    set_component_symbol_text_attributes,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolTextUpdate:
    """Metadata for one embedded symbol text edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    text_attribute: SymbolTextMetadata


SERVICE_SPEC = ServiceSpec(
    name="set_component_symbol_text",
    title="Set Component Symbol Text",
    summary="Update one embedded symbol text item, including layout and style attributes.",
    phase="implemented",
    read_only=False,
)


def set_component_symbol_text(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    text_index: int | None = None,
    text_role: str | None = None,
    text: str | None = None,
    position_x: int | None = None,
    position_y: int | None = None,
    size: int | None = None,
    rotation_code: int | None = None,
    is_comment: bool | None = None,
    color_code: str | None = None,
    output_path: str | Path | None = None,
) -> ComponentSymbolTextUpdate:
    """Update one embedded symbol text item and persist the edited schematic."""

    if (position_x is None) != (position_y is None):
        raise ValueError("position_x and position_y must be provided together.")
    position = None if position_x is None or position_y is None else (position_x, position_y)

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    text_attribute = set_component_symbol_text_attributes(
        editor,
        reference=reference,
        text_index=text_index,
        text_role=text_role,
        text=text,
        position=position,
        size=size,
        rotation_code=rotation_code,
        is_comment=is_comment,
        color_code=color_code,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return ComponentSymbolTextUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        text_attribute=text_attribute,
    )


__all__ = ["SERVICE_SPEC", "ComponentSymbolTextUpdate", "set_component_symbol_text"]
