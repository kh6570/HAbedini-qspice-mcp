"""Service for updating one component value inside a subcircuit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic, save_editor_as
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.subcircuit._navigation import (
    build_instance_component_reference,
    default_definition_output_name,
    normalize_component_reference,
    resolve_subcircuit_target,
)

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services.subcircuit.read_subcircuit import SubcircuitScope


@dataclass(frozen=True, slots=True)
class SubcircuitComponentValueUpdate:
    """Metadata for one subcircuit-scoped component value edit."""

    schematic_path: Path
    output_path: Path
    instance_path: tuple[str, ...]
    reference: str
    component_reference: str
    scope: SubcircuitScope
    value: str


SERVICE_SPEC = ServiceSpec(
    name="set_subcircuit_component_value",
    title="Set Subcircuit Component Value",
    summary="Update one component value inside a subcircuit instance or definition.",
    phase="implemented",
    read_only=False,
)


def set_subcircuit_component_value(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    component_reference: str,
    value: str | int | float | complex,
    scope: SubcircuitScope = "instance",
    instance_path: tuple[str, ...] | list[str] | None = None,
    output_path: str | Path | None = None,
) -> SubcircuitComponentValueUpdate:
    """Update one component value with explicit subcircuit scope semantics."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    _, subeditor, normalized_instance_path, normalized_reference = resolve_subcircuit_target(
        editor,
        reference=reference,
        instance_path=instance_path,
    )
    normalized_component_reference = normalize_component_reference(component_reference)
    if scope == "instance":
        editor.set_component_value(
            build_instance_component_reference(
                reference=normalized_reference,
                component_reference=normalized_component_reference,
                instance_path=normalized_instance_path,
            ),
            value,
        )
        saved_path = save_edited_schematic(
            editor,
            schematic_path=resolved_path,
            workspace_root=workspace_root,
            output_path=output_path,
        )
    else:
        if output_path is None:
            raise ValueError(
                "output_path is required for definition-scoped edits so the "
                "resolved definition can be saved explicitly."
            )
        subeditor.set_component_value(normalized_component_reference, value)
        saved_path = save_editor_as(
            subeditor,
            workspace_root=workspace_root,
            output_path=output_path,
            default=resolved_path.with_name(
                default_definition_output_name(
                    reference=normalized_reference,
                    instance_path=normalized_instance_path,
                )
            ),
        )
    return SubcircuitComponentValueUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        instance_path=normalized_instance_path,
        reference=normalized_reference,
        component_reference=normalized_component_reference,
        scope=scope,
        value=str(value),
    )


__all__ = ["SERVICE_SPEC", "SubcircuitComponentValueUpdate", "set_subcircuit_component_value"]
