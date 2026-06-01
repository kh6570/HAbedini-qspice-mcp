"""Service for rotating one placed schematic component."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    set_component_rotation as apply_component_rotation,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentRotationUpdate:
    """Metadata for one component rotation edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    rotation_degrees: int


SERVICE_SPEC = ServiceSpec(
    name="set_component_rotation",
    title="Set Component Rotation",
    summary="Rotate one placed schematic component in 45-degree steps without moving it.",
    phase="implemented",
    read_only=False,
)


def set_component_rotation(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    rotation_degrees: int,
    output_path: str | Path | None = None,
) -> ComponentRotationUpdate:
    """Rotate one component and persist the edited schematic."""

    applied_rotation: int | None = None

    def apply_rotation_edit(editor: object) -> None:
        nonlocal applied_rotation
        applied_rotation = apply_component_rotation(
            cast("Any", editor),
            reference=reference,
            rotation_degrees=rotation_degrees,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_rotation_edit,
    )
    if applied_rotation is None:
        raise RuntimeError("Component rotation did not report an applied angle.")
    return ComponentRotationUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        rotation_degrees=applied_rotation,
    )


__all__ = ["SERVICE_SPEC", "ComponentRotationUpdate", "set_component_rotation"]
