"""Service for resetting embedded symbol text to upright readable orientation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    NormalizedSymbolTextRotation,
    component_rotation_index_to_degrees,
    symbol_text_rotation_code_for_degrees,
)
from qspice_mcp.services._backends.schematic_editor import (
    normalize_component_symbol_text_rotation as apply_symbol_text_normalization,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

SERVICE_SPEC = ServiceSpec(
    name="normalize_component_text_rotation",
    title="Normalize Component Text Rotation",
    summary=(
        "Reset refdes/value symbol text to left-to-right readable orientation, "
        "compensating for the placed component body rotation when needed."
    ),
    phase="implemented",
    read_only=False,
)


@dataclass(frozen=True, slots=True)
class NormalizedComponentTextRotation:
    """Summary of one symbol text normalization run."""

    schematic_path: Path
    output_path: Path
    reference: str
    component_rotation_degrees: int
    compensate_component_rotation: bool
    target_rotation_code: int
    updated_count: int
    skipped_count: int
    text_attributes: tuple[NormalizedSymbolTextRotation, ...]


def _resolve_target_rotation_code(
    *,
    component_rotation_degrees: int,
    compensate_component_rotation: bool,
    upright_rotation_code: int | None,
) -> int:
    if compensate_component_rotation:
        return symbol_text_rotation_code_for_degrees((-component_rotation_degrees) % 360)
    if upright_rotation_code is not None:
        return upright_rotation_code
    return symbol_text_rotation_code_for_degrees(0)


def normalize_component_text_rotation(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    text_roles: tuple[str, ...] | list[str] | None = None,
    compensate_component_rotation: bool = True,
    upright_rotation_code: int | None = None,
    output_path: str | Path | None = None,
) -> NormalizedComponentTextRotation:
    """Normalize embedded refdes/value text rotation for one schematic component."""

    roles = tuple(text_roles) if text_roles is not None else ("reference", "value")
    component_rotation_degrees: int | None = None
    normalized_rows: tuple[NormalizedSymbolTextRotation, ...] = ()

    def apply_edit(editor: object) -> None:
        nonlocal component_rotation_degrees, normalized_rows
        editor_obj = cast("Any", editor)
        _position, rotation_index = editor_obj.get_component_position(reference.strip())
        del _position
        component_rotation_degrees = component_rotation_index_to_degrees(int(rotation_index))
        normalized_rows = apply_symbol_text_normalization(
            editor_obj,
            reference=reference,
            text_roles=roles,
            compensate_component_rotation=compensate_component_rotation,
            upright_rotation_code=upright_rotation_code,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_edit,
    )
    if component_rotation_degrees is None:
        raise RuntimeError("Symbol text normalization did not run.")

    target_rotation_code = _resolve_target_rotation_code(
        component_rotation_degrees=component_rotation_degrees,
        compensate_component_rotation=compensate_component_rotation,
        upright_rotation_code=upright_rotation_code,
    )
    updated_count = sum(1 for item in normalized_rows if item.updated)
    skipped_count = sum(1 for item in normalized_rows if not item.updated)
    return NormalizedComponentTextRotation(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference.strip(),
        component_rotation_degrees=component_rotation_degrees,
        compensate_component_rotation=compensate_component_rotation,
        target_rotation_code=target_rotation_code,
        updated_count=updated_count,
        skipped_count=skipped_count,
        text_attributes=normalized_rows,
    )


__all__ = [
    "SERVICE_SPEC",
    "NormalizedComponentTextRotation",
    "normalize_component_text_rotation",
]
