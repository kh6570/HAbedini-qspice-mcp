"""Service for updating component-local parameters in a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentParameterUpdate:
    """Metadata for one component parameter edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    parameter_names: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="set_component_parameters",
    title="Set Component Parameters",
    summary="Update one or more component-local parameters in a schematic.",
    phase="implemented",
    read_only=False,
)


def set_component_parameters(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    parameters: Mapping[str, object],
    output_path: str | Path | None = None,
) -> ComponentParameterUpdate:
    """Update one or more component parameters and persist the edited schematic."""

    if not parameters:
        raise ValueError("At least one component parameter is required.")

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=lambda editor: editor.set_component_parameters(reference, **dict(parameters)),
    )
    return ComponentParameterUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        parameter_names=tuple(str(name) for name in parameters),
    )


__all__ = ["SERVICE_SPEC", "ComponentParameterUpdate", "set_component_parameters"]
