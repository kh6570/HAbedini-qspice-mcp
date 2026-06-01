"""Service for updating one schematic-level `.param` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SchematicParameterUpdate:
    """Metadata for one schematic parameter edit."""

    schematic_path: Path
    output_path: Path
    name: str
    value: str


SERVICE_SPEC = ServiceSpec(
    name="set_parameter",
    title="Set Parameter",
    summary="Update one schematic-level `.param` directive.",
    phase="implemented",
    read_only=False,
)


def set_parameter(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    name: str,
    value: str | int | float | complex,
    output_path: str | Path | None = None,
) -> SchematicParameterUpdate:
    """Update one schematic-level parameter and persist the edited schematic."""

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=lambda editor: editor.set_parameter(name, value),
    )
    return SchematicParameterUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        name=name,
        value=str(value),
    )


__all__ = ["SERVICE_SPEC", "SchematicParameterUpdate", "set_parameter"]
