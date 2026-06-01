"""Service for updating one component symbol pin item."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolPinMetadata,
    open_schematic_editor,
    set_component_symbol_pin_metadata,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentSymbolPinUpdate:
    """Metadata for one embedded symbol pin edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    pin: SymbolPinMetadata


SERVICE_SPEC = ServiceSpec(
    name="set_component_symbol_pin",
    title="Set Component Symbol Pin",
    summary="Update one embedded symbol pin name, label geometry, or pin-kind metadata.",
    phase="implemented",
    read_only=False,
)


def set_component_symbol_pin(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    pin_index: int | None = None,
    pin_name: str | None = None,
    new_pin_name: str | None = None,
    label_position_x: int | None = None,
    label_position_y: int | None = None,
    text_size: int | None = None,
    label_anchor_code: int | None = None,
    pin_kind_code: int | None = None,
    color_code: str | None = None,
    aux_code: int | None = None,
    behavioral_net_override: str | None = None,
    clear_behavioral_net_override: bool = False,
    output_path: str | Path | None = None,
) -> ComponentSymbolPinUpdate:
    """Update one embedded symbol pin item and persist the edited schematic."""

    if (label_position_x is None) != (label_position_y is None):
        raise ValueError("label_position_x and label_position_y must be provided together.")
    label_position = (
        None
        if label_position_x is None or label_position_y is None
        else (label_position_x, label_position_y)
    )

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    pin = set_component_symbol_pin_metadata(
        editor,
        reference=reference,
        pin_index=pin_index,
        pin_name=pin_name,
        new_pin_name=new_pin_name,
        label_position=label_position,
        text_size=text_size,
        label_anchor_code=label_anchor_code,
        pin_kind_code=pin_kind_code,
        color_code=color_code,
        aux_code=aux_code,
        behavioral_net_override=behavioral_net_override,
        clear_behavioral_net_override=clear_behavioral_net_override,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return ComponentSymbolPinUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        pin=pin,
    )


__all__ = ["SERVICE_SPEC", "ComponentSymbolPinUpdate", "set_component_symbol_pin"]
