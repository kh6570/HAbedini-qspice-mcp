"""Apply a workspace JSON layout specification to place schematic components."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.schematic._layout import PlacedComponent, load_placed_components
from qspice_mcp.services.schematic._layout_spec import (
    ResolvedLayoutPlacement,
    load_layout_spec_file,
    resolve_layout_placements,
)
from qspice_mcp.services.schematic.add_component import AddedComponent, add_component
from qspice_mcp.services.service_spec import ServiceSpec

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
    schematic_path: Path,
    workspace_root: Path,
    row: ResolvedLayoutPlacement,
    output_path: Path | None,
    skip_existing: bool,
    existing_refs: frozenset[str],
) -> tuple[AppliedLayoutComponent, Path | None, bool]:
    if skip_existing and row.reference is not None and row.reference in existing_refs:
        return (
            AppliedLayoutComponent(
                reference=row.reference,
                component_kind=row.component_kind,
                placement=row.placement,
                position_x=row.position_x,
                position_y=row.position_y,
                rotation_degrees=row.rotation_degrees,
                skipped_existing=True,
            ),
            output_path,
            True,
        )
    added: AddedComponent = add_component(
        schematic_path,
        workspace_root=workspace_root,
        component_kind=row.component_kind,
        reference=row.reference,
        value=row.value,
        position_x=row.position_x,
        position_y=row.position_y,
        rotation_degrees=row.rotation_degrees,
        net_name=row.net_name,
        output_path=output_path,
    )
    return (
        AppliedLayoutComponent(
            reference=added.reference,
            component_kind=added.component_kind,
            placement=row.placement,
            position_x=added.position_x,
            position_y=added.position_y,
            rotation_degrees=added.rotation_degrees,
            skipped_existing=False,
        ),
        added.output_path,
        False,
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
    existing_refs = _existing_references(placed)
    resolved_rows = resolve_layout_placements(spec, placed_components=placed)

    applied: list[AppliedLayoutComponent] = []
    skipped = 0
    latest_output: Path | None = None
    current_output: Path | None = Path(output_path) if output_path is not None else None
    for row in resolved_rows:
        component_row, latest_output, was_skipped = _apply_resolved_row(
            schematic_path=resolved_schematic,
            workspace_root=workspace_root,
            row=row,
            output_path=current_output,
            skip_existing=skip_existing,
            existing_refs=existing_refs,
        )
        applied.append(component_row)
        if was_skipped:
            skipped += 1
        else:
            current_output = latest_output if latest_output is not None else current_output
            if component_row.reference is not None:
                existing_refs = frozenset({*existing_refs, component_row.reference})

    if latest_output is None:
        latest_output = resolved_schematic

    applied_count = sum(1 for item in applied if not item.skipped_existing)
    return AppliedSchematicLayoutSpec(
        schematic_path=resolved_schematic,
        spec_path=resolved_spec_path,
        output_path=latest_output,
        schema_version=spec.schema_version,
        applied_count=applied_count,
        skipped_existing_count=skipped,
        components=tuple(applied),
    )


__all__ = [
    "SERVICE_SPEC",
    "AppliedLayoutComponent",
    "AppliedSchematicLayoutSpec",
    "apply_schematic_layout_spec",
]
