# In the name of God, the Most Gracious, the Most Merciful
"""Apply a workspace JSON layout specification to place schematic components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._backends.schematic_editor import add_simple_component
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.schematic._layout import PlacedComponent, load_placed_components
from qspice_mcp.services.schematic._layout_spec import (
    ResolvedLayoutPlacement,
    load_layout_spec_file,
    resolve_layout_placements,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol

SERVICE_SPEC = ServiceSpec(
    name="apply_schematic_layout_spec",
    title="Apply Schematic Layout Spec",
    summary=(
        "Place schematic components in batch from a workspace JSON layout specification "
        "using auto, grid, or absolute placement modes."
    ),
    phase="implemented",
    read_only=False,
)


@dataclass(frozen=True, slots=True)
class AppliedLayoutComponent:
    """One component row applied from a layout specification."""

    reference: str | None
    component_kind: str
    placement: str
    position_x: int
    position_y: int
    rotation_degrees: int
    skipped_existing: bool


@dataclass(frozen=True, slots=True)
class AppliedSchematicLayoutSpec:
    """Summary of one layout-spec application run."""

    schematic_path: Path
    spec_path: Path
    output_path: Path
    schema_version: int
    applied_count: int
    skipped_existing_count: int
    components: tuple[AppliedLayoutComponent, ...]


def _existing_references(placed: tuple[PlacedComponent, ...]) -> frozenset[str]:
    return frozenset(item.reference for item in placed)


def _apply_resolved_row(
    *,
    editor: _QschEditorProtocol,
    row: ResolvedLayoutPlacement,
    skip_existing: bool,
    existing_refs: frozenset[str],
) -> AppliedLayoutComponent:
    if skip_existing and row.reference is not None and row.reference in existing_refs:
        return AppliedLayoutComponent(
            reference=row.reference,
            component_kind=row.component_kind,
            placement=row.placement,
            position_x=row.position_x,
            position_y=row.position_y,
            rotation_degrees=row.rotation_degrees,
            skipped_existing=True,
        )
    normalized_kind = add_simple_component(
        editor,
        component_kind=row.component_kind,
        reference=row.reference,
        value=row.value,
        position=(row.position_x, row.position_y),
        rotation_degrees=row.rotation_degrees,
        net_name=row.net_name,
    )
    return AppliedLayoutComponent(
        reference=row.reference,
        component_kind=normalized_kind,
        placement=row.placement,
        position_x=row.position_x,
        position_y=row.position_y,
        rotation_degrees=row.rotation_degrees,
        skipped_existing=False,
    )


def apply_schematic_layout_spec(
    schematic_path: str | Path,
    spec_path: str | Path,
    *,
    workspace_root: Path,
    skip_existing: bool = True,
    output_path: str | Path | None = None,
) -> AppliedSchematicLayoutSpec:
    """Place components listed in one workspace JSON layout specification."""

    resolved_spec_path, spec = load_layout_spec_file(
        spec_path,
        workspace_root=workspace_root,
    )
    if spec.schematic_path is not None:
        spec_schematic = spec.schematic_path.strip()
        requested = str(schematic_path).strip()
        if spec_schematic and requested and spec_schematic != requested:
            raise ValidationError(
                "Layout spec schematic_path does not match the requested schematic_path: "
                f"{spec_schematic!r} vs {requested!r}."
            )

    resolved_schematic, placed = load_placed_components(
        schematic_path,
        workspace_root=workspace_root,
    )
    resolved_rows = resolve_layout_placements(spec, placed_components=placed)

    applied: list[AppliedLayoutComponent] = []

    def apply_rows(editor: _QschEditorProtocol) -> None:
        existing_refs = _existing_references(placed)
        for row in resolved_rows:
            component_row = _apply_resolved_row(
                editor=editor,
                row=row,
                skip_existing=skip_existing,
                existing_refs=existing_refs,
            )
            applied.append(component_row)
            if not component_row.skipped_existing and component_row.reference is not None:
                existing_refs = frozenset({*existing_refs, component_row.reference})

    # Persist once, after every row succeeds. A failed row leaves both the
    # source and any requested destination unchanged.
    _, latest_output = edit_schematic(
        resolved_schematic,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_rows,
    )

    applied_count = sum(1 for item in applied if not item.skipped_existing)
    return AppliedSchematicLayoutSpec(
        schematic_path=resolved_schematic,
        spec_path=resolved_spec_path,
        output_path=latest_output,
        schema_version=spec.schema_version,
        applied_count=applied_count,
        skipped_existing_count=len(applied) - applied_count,
        components=tuple(applied),
    )


__all__ = [
    "SERVICE_SPEC",
    "AppliedLayoutComponent",
    "AppliedSchematicLayoutSpec",
    "apply_schematic_layout_spec",
]
