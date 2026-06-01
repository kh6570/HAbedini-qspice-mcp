"""Service for updating one component value in a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentValueUpdate:
    """Metadata for one component value edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    value: str


SERVICE_SPEC = ServiceSpec(
    name="set_component_value",
    title="Set Component Value",
    summary="Update the value field of one schematic component.",
    phase="implemented",
    read_only=False,
)


def set_component_value(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    value: str | int | float | complex,
    output_path: str | Path | None = None,
) -> ComponentValueUpdate:
    """Update one component value and persist the edited schematic."""

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=lambda editor: editor.set_component_value(reference, value),
    )
    return ComponentValueUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        value=str(value),
    )


__all__ = ["SERVICE_SPEC", "ComponentValueUpdate", "set_component_value"]
