"""Service for adding one directive to a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.clean_room_schematic import (
    add_instruction_to_supported_schematic,
)
from qspice_mcp.services._backends.schematic_editor import resolve_schematic_output_path
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@dataclass(frozen=True, slots=True)
class InstructionAdd:
    """Metadata for one added instruction."""

    schematic_path: Path
    output_path: Path
    instruction: str


SERVICE_SPEC = ServiceSpec(
    name="add_instruction",
    title="Add Instruction",
    summary="Append one directive or analysis instruction to a schematic.",
    phase="implemented",
    read_only=False,
)


def add_instruction(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    instruction: str,
    output_path: str | Path | None = None,
) -> InstructionAdd:
    """Add one instruction and persist the edited schematic."""

    resolved_workspace = workspace_root.resolve(strict=False)
    try:
        resolved_path, saved_path = edit_schematic(
            schematic_path,
            workspace_root=resolved_workspace,
            output_path=output_path,
            apply_edit=lambda editor: _apply_add_instruction(editor, instruction),
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
        add_instruction_to_supported_schematic(
            resolved_path,
            saved_path,
            instruction=instruction,
        )
    return InstructionAdd(
        schematic_path=resolved_path,
        output_path=saved_path,
        instruction=instruction,
    )


def _apply_add_instruction(editor: Any, instruction: str) -> None:
    editor.add_instruction(instruction)
    editor.updated = True


__all__ = ["SERVICE_SPEC", "InstructionAdd", "add_instruction"]
