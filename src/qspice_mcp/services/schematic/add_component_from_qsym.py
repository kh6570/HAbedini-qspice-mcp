"""Service for placing one standalone `.qsym` symbol file into a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    add_qsym_symbol_component,
    read_qsym_symbol_tag,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedQsymComponent:
    """Metadata for one component placed from a standalone `.qsym` file."""

    schematic_path: Path
    output_path: Path
    qsym_path: Path
    reference: str
    symbol_name: str
    type_name: str | None
    library_file: str | None
    value: str | None
    pin_names: tuple[str, ...]
    position_x: int
    position_y: int
    rotation_degrees: int


SERVICE_SPEC = ServiceSpec(
    name="add_component_from_qsym",
    title="Add Component From Qsym",
    summary=(
        "Place one component into a schematic from a standalone `.qsym` symbol "
        "file, embedding the symbol and assigning a new reference designator."
    ),
    phase="implemented",
    read_only=False,
)


def add_component_from_qsym(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    qsym_path: str | Path,
    reference: str,
    position_x: int = 0,
    position_y: int = 0,
    rotation_degrees: int = 0,
    value: str | None = None,
    output_path: str | Path | None = None,
) -> AddedQsymComponent:
    """Place one `.qsym` symbol as a new component and persist the schematic."""

    resolved_qsym_path = validate_existing_file(
        qsym_path,
        workspace_root=workspace_root,
        suffixes=(".qsym",),
    )
    symbol_tag = read_qsym_symbol_tag(resolved_qsym_path)

    applied: Any = None

    def apply_qsym_edit(editor: object) -> None:
        nonlocal applied
        applied = add_qsym_symbol_component(
            cast("Any", editor),
            symbol_tag=symbol_tag,
            reference=reference,
            position=(int(position_x), int(position_y)),
            value=value,
            rotation_degrees=rotation_degrees,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_qsym_edit,
    )
    if applied is None:
        raise RuntimeError("Qsym component placement did not report a result.")
    return AddedQsymComponent(
        schematic_path=resolved_path,
        output_path=saved_path,
        qsym_path=resolved_qsym_path,
        reference=applied.reference,
        symbol_name=applied.symbol_name,
        type_name=applied.type_name,
        library_file=applied.library_file,
        value=applied.value,
        pin_names=applied.pin_names,
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=rotation_degrees,
    )


__all__ = ["SERVICE_SPEC", "AddedQsymComponent", "add_component_from_qsym"]
