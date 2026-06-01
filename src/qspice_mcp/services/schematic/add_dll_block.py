"""Service for inserting one `.DLL` custom-device block into a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import add_dll_block as add_dll_block_backend
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


@dataclass(frozen=True, slots=True)
class AddedDllBlock:
    """Metadata for one inserted `.DLL` custom-device block."""

    schematic_path: Path
    output_path: Path
    reference: str
    device_name: str
    input_pin_names: tuple[str, ...]
    output_pin_names: tuple[str, ...]
    position_x: int
    position_y: int
    rotation_degrees: int


SERVICE_SPEC = ServiceSpec(
    name="add_dll_block",
    title="Add DLL Block",
    summary=(
        "Insert one `.DLL` custom-device block into a schematic with starter input and output pins."
    ),
    phase="implemented",
    read_only=False,
)


def add_dll_block(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    device_name: str,
    input_pin_names: tuple[str, ...] | list[str] = ("in0",),
    output_pin_names: tuple[str, ...] | list[str] = ("out0",),
    position_x: int = 0,
    position_y: int = 0,
    rotation_degrees: int = 0,
    output_path: str | Path | None = None,
) -> AddedDllBlock:
    """Insert one `.DLL` block and persist the edited schematic."""

    normalized_input_pin_names: tuple[str, ...] = ()
    normalized_output_pin_names: tuple[str, ...] = ()

    def apply_dll_block_edit(editor: _QschEditorProtocol) -> None:
        nonlocal normalized_input_pin_names, normalized_output_pin_names
        normalized_input_pin_names, normalized_output_pin_names = add_dll_block_backend(
            editor,
            reference=reference,
            device_name=device_name,
            input_pin_names=input_pin_names,
            output_pin_names=output_pin_names,
            position=(position_x, position_y),
            rotation_degrees=rotation_degrees,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_dll_block_edit,
    )
    return AddedDllBlock(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference.strip(),
        device_name=device_name.strip(),
        input_pin_names=normalized_input_pin_names,
        output_pin_names=normalized_output_pin_names,
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=rotation_degrees,
    )


__all__ = ["SERVICE_SPEC", "AddedDllBlock", "add_dll_block"]
