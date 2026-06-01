"""Service for moving one `.DLL` pin between the input and output role presets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    SymbolPinMetadata,
    open_schematic_editor,
    set_dll_block_pin_role_metadata,
)
from qspice_mcp.services._internals.dll_contracts import dll_pin_direction_from_symbol_pin
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DllBlockPinRoleUpdate:
    """Metadata for one `.DLL` block pin role update."""

    schematic_path: Path
    output_path: Path
    reference: str
    pin: SymbolPinMetadata
    input_pin_names: tuple[str, ...]
    output_pin_names: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="set_dll_block_pin_role",
    title="Set DLL Block Pin Role",
    summary="Move one `.DLL` block pin into the input or output role preset.",
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


def set_dll_block_pin_role(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    pin_role: str,
    pin_index: int | None = None,
    pin_name: str | None = None,
    output_path: str | Path | None = None,
) -> DllBlockPinRoleUpdate:
    """Move one `.DLL` block pin into a higher-level role preset and persist it."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    pin, metadata = set_dll_block_pin_role_metadata(
        editor,
        reference=reference,
        pin_index=pin_index,
        pin_name=pin_name,
        pin_role=pin_role,
    )
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    input_pin_names, output_pin_names = _group_dll_pin_names(metadata.pins)
    return DllBlockPinRoleUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        pin=pin,
        input_pin_names=input_pin_names,
        output_pin_names=output_pin_names,
    )


__all__ = ["SERVICE_SPEC", "DllBlockPinRoleUpdate", "set_dll_block_pin_role"]
