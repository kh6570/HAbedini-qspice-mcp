"""Service for removing one directive from a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.clean_room_schematic import (
    remove_instruction_from_supported_schematic,
)
from qspice_mcp.services._backends.schematic_editor import resolve_schematic_output_path
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


@dataclass(frozen=True, slots=True)
class InstructionRemoval:
    """Metadata for one removed instruction."""

    schematic_path: Path
    output_path: Path
    instruction: str
    regex: bool


SERVICE_SPEC = ServiceSpec(
    name="remove_instruction",
    title="Remove Instruction",
    summary="Remove one exact or regex-matched directive from a schematic.",
    phase="implemented",
    read_only=False,
)


def remove_instruction(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    instruction: str,
    output_path: str | Path | None = None,
    regex: bool = False,
) -> InstructionRemoval:
    """Remove one instruction and persist the edited schematic."""

    removed = False

    def _remove(editor: _QschEditorProtocol) -> None:
        nonlocal removed
        if regex:
            removed = editor.remove_Xinstruction(instruction)
        else:
            removed = editor.remove_instruction(instruction)
        editor.updated = True

    resolved_workspace = workspace_root.resolve(strict=False)
    try:
        resolved_path, saved_path = edit_schematic(
            schematic_path,
            workspace_root=resolved_workspace,
            output_path=output_path,
            apply_edit=_remove,
        )
    except BackendUnavailableError:
        resolved_path = validate_existing_file(
            schematic_path,
            workspace_root=resolved_workspace,
            suffixes=(".qsch",),
        )
        saved_path = resolve_schematic_output_path(
            output_path,
            workspace_root=resolved_workspace,
            default=resolved_path,
        )
        removed = remove_instruction_from_supported_schematic(
            resolved_path,
            saved_path,
            instruction=instruction,
            regex=regex,
        )
    if not removed:
        raise ValueError(f"Instruction was not found in the schematic: {instruction}")
    return InstructionRemoval(
        schematic_path=resolved_path,
        output_path=saved_path,
        instruction=instruction,
        regex=regex,
    )


__all__ = ["SERVICE_SPEC", "InstructionRemoval", "remove_instruction"]
