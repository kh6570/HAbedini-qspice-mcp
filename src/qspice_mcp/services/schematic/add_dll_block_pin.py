"""Service for inserting one pin into an existing `.DLL` block symbol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolPinMetadata,
    add_dll_block_pin_metadata,
    open_schematic_editor,
)
from qspice_mcp.services._internals.dll_contracts import dll_pin_direction_from_symbol_pin
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedDllBlockPin:
    """Metadata for one inserted `.DLL` block pin."""

    schematic_path: Path
    output_path: Path
    reference: str
    pin: SymbolPinMetadata
    input_pin_names: tuple[str, ...]
    output_pin_names: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="add_dll_block_pin",
    title="Add DLL Block Pin",
    summary="Insert one input or output pin into an existing `.DLL` block symbol.",
    phase="implemented",
    read_only=False,
)


def _group_dll_pin_names(
    pin_metadata: tuple[SymbolPinMetadata, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split symbol pin names into input and output groups."""

    input_pin_names = tuple(
        pin.name for pin in pin_metadata if dll_pin_direction_from_symbol_pin(pin) == "input"
    )
    output_pin_names = tuple(
        pin.name for pin in pin_metadata if dll_pin_direction_from_symbol_pin(pin) == "output"
    )
    return input_pin_names, output_pin_names


def add_dll_block_pin(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    pin_name: str,
    direction: str,
    insert_index: int | None = None,
    output_path: str | Path | None = None,
) -> AddedDllBlockPin:
    """Insert one `.DLL` block pin and persist the edited schematic."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    pin, metadata = add_dll_block_pin_metadata(
        editor,
        reference=reference,
        pin_name=pin_name,
        direction=direction,
        insert_index=insert_index,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    input_pin_names, output_pin_names = _group_dll_pin_names(metadata.pins)
    return AddedDllBlockPin(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        pin=pin,
        input_pin_names=input_pin_names,
        output_pin_names=output_pin_names,
    )


__all__ = ["SERVICE_SPEC", "AddedDllBlockPin", "add_dll_block_pin"]
