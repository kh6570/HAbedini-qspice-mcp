"""Service for cloning a component from a template schematic into a target."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services._backends.schematic_editor import (
    clone_library_component,
    open_schematic_editor,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class AddedLibraryComponent:
    """Metadata for one cloned library component."""

    schematic_path: Path
    output_path: Path
    template_path: Path
    reference: str
    symbol_name: str
    type_name: str | None
    library_file: str | None
    value: str | None
    pin_names: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="add_library_component",
    title="Add Library Component",
    summary="Clone one component symbol from a template schematic into a target schematic.",
    phase="implemented",
    read_only=False,
)


def add_library_component(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    template_path: str | Path,
    template_reference: str,
    reference: str,
    position_x: int = 0,
    position_y: int = 0,
    value: str | None = None,
    output_path: str | Path | None = None,
) -> AddedLibraryComponent:
    """Clone one component from a template `.qsch` into the target and persist it."""

    resolved_workspace = workspace_root.resolve(strict=False)
    template_editor, resolved_template, _ = open_schematic_editor(
        template_path,
        workspace_root=resolved_workspace,
    )
    try:
        template_component = template_editor.get_component(template_reference)
    except Exception as exc:
        raise QSpiceError(
            f"Template schematic {resolved_template.name} has no component {template_reference!r}."
        ) from exc
    template_tag = cast("Any", template_component.attributes.get("tag"))

    applied: Any = None

    def apply_clone_edit(editor: object) -> None:
        nonlocal applied
        applied = clone_library_component(
            cast("Any", editor),
            template_component_tag=template_tag,
            reference=reference,
            position=(int(position_x), int(position_y)),
            value=value,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_clone_edit,
    )
    if applied is None:
        raise RuntimeError("Library component clone did not report a result.")
    return AddedLibraryComponent(
        schematic_path=resolved_path,
        output_path=saved_path,
        template_path=resolved_template,
        reference=applied.reference,
        symbol_name=applied.symbol_name,
        type_name=applied.type_name,
        library_file=applied.library_file,
        value=applied.value,
        pin_names=applied.pin_names,
    )


__all__ = ["SERVICE_SPEC", "AddedLibraryComponent", "add_library_component"]
