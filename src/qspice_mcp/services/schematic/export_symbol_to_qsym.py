"""Service for exporting one embedded component symbol to a standalone `.qsym` file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    export_component_symbol_tag,
    open_schematic_editor,
    read_component_symbol_metadata,
    write_qsym_file,
)
from qspice_mcp.services._shared.paths import resolve_workspace_output_path
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExportedQsymSymbol:
    """Metadata for one exported standalone `.qsym` symbol file."""

    schematic_path: Path
    reference: str
    symbol_name: str
    output_path: Path
    type_name: str | None
    pin_names: tuple[str, ...]
    byte_count: int


SERVICE_SPEC = ServiceSpec(
    name="export_symbol_to_qsym",
    title="Export Symbol To Qsym",
    summary=(
        "Export one embedded component symbol from a schematic to a standalone "
        "`.qsym` symbol file for reuse across schematics and external tools."
    ),
    phase="implemented",
    read_only=False,
)


def export_symbol_to_qsym(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    output_path: str | Path | None = None,
    symbol_name: str | None = None,
) -> ExportedQsymSymbol:
    """Export one component's embedded symbol as a standalone `.qsym` file."""

    resolved_workspace = workspace_root.resolve(strict=False)
    editor, resolved_schematic_path, _ = open_schematic_editor(
        schematic_path,
        workspace_root=resolved_workspace,
    )
    metadata = read_component_symbol_metadata(editor, reference=reference)
    exported_tag, resolved_symbol_name = export_component_symbol_tag(
        editor,
        reference=reference,
        symbol_name=symbol_name,
    )

    resolved_output_path = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=resolved_schematic_path.parent / f"{resolved_symbol_name}.qsym",
        suffixes=(".qsym",),
    )
    write_qsym_file(exported_tag, resolved_output_path)

    return ExportedQsymSymbol(
        schematic_path=resolved_schematic_path,
        reference=reference,
        symbol_name=resolved_symbol_name,
        output_path=resolved_output_path,
        type_name=metadata.type_name,
        pin_names=tuple(pin.name for pin in metadata.pins),
        byte_count=resolved_output_path.stat().st_size,
    )


__all__ = ["SERVICE_SPEC", "ExportedQsymSymbol", "export_symbol_to_qsym"]
