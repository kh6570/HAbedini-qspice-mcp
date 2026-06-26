"""Parse and resolve schematic layout specification documents (JSON v1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic._layout import (
    DEFAULT_CLEARANCE,
    DEFAULT_ORIGIN_X,
    DEFAULT_ORIGIN_Y,
    GRID_STEP_X,
    GRID_STEP_Y,
    PlacedComponent,
    component_half_extents,
    suggest_next_component_placement,
)

if TYPE_CHECKING:
    from pathlib import Path

LAYOUT_SPEC_SCHEMA_VERSION = 1
_SUPPORTED_PLACEMENT_MODES = frozenset({"auto", "grid", "absolute"})


@dataclass(frozen=True, slots=True)
class LayoutGridSpec:
    """Grid defaults shared by auto and grid-column placement modes."""

    origin_x: int
    origin_y: int
    step_x: int
    step_y: int
    clearance_units: int


@dataclass(frozen=True, slots=True)
class LayoutComponentSpec:
    """One component row from a layout specification."""

    reference: str | None
    component_kind: str
    value: str | int | float | None
    net_name: str | None
    placement: str
    position_x: int | None
    position_y: int | None
    grid_column: int | None
    grid_row: int | None
    rotation_degrees: int


@dataclass(frozen=True, slots=True)
class SchematicLayoutSpec:
    """Validated layout specification document."""

    schema_version: int
    schematic_path: str | None
    grid: LayoutGridSpec
    components: tuple[LayoutComponentSpec, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedLayoutPlacement:
    """Concrete coordinates resolved from one layout component row."""

    reference: str | None
    component_kind: str
    value: str | int | float | None
    net_name: str | None
    position_x: int
    position_y: int
    rotation_degrees: int
    placement: str


def example_layout_spec_document() -> dict[str, object]:
    """Return the canonical v1 example document shipped with the server."""

    bundled = files("qspice_mcp.data.layout_specs").joinpath("scratch_power_stage.v1.json")
    document: dict[str, object] = json.loads(bundled.read_text(encoding="utf-8"))
    return document


def layout_spec_json_schema() -> dict[str, object]:
    """Return a JSON Schema fragment describing layout spec v1."""

    return {
        "type": "object",
        "required": ["schema_version", "components"],
        "properties": {
            "schema_version": {"type": "integer", "const": LAYOUT_SPEC_SCHEMA_VERSION},
            "schematic_path": {"type": "string"},
            "notes": {"type": "array", "items": {"type": "string"}},
            "grid": {
                "type": "object",
                "properties": {
                    "origin_x": {"type": "integer"},
                    "origin_y": {"type": "integer"},
                    "step_x": {"type": "integer"},
                    "step_y": {"type": "integer"},
                    "clearance_units": {"type": "integer"},
                },
            },
            "components": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["component_kind"],
                    "properties": {
                        "reference": {"type": "string"},
                        "component_kind": {"type": "string"},
                        "value": {},
                        "net_name": {"type": "string"},
                        "placement": {
                            "type": "string",
                            "enum": ["auto", "grid", "absolute"],
                        },
                        "position_x": {"type": "integer"},
                        "position_y": {"type": "integer"},
                        "grid_column": {"type": "integer", "minimum": 0},
                        "grid_row": {"type": "integer", "minimum": 0},
                        "rotation_degrees": {"type": "integer"},
                    },
                },
            },
        },
    }


def _require_mapping(value: object, *, field_name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field_name} must be a JSON object.")
    return value


def _optional_int(value: object, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer.")
    return value


def _grid_int(grid: dict[str, object], key: str, default: int) -> int:
    value = grid.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"grid.{key} must be an integer.")
    return value


def _parse_grid(raw: object) -> LayoutGridSpec:
    if raw is None:
        return LayoutGridSpec(
            origin_x=DEFAULT_ORIGIN_X,
            origin_y=DEFAULT_ORIGIN_Y,
            step_x=GRID_STEP_X,
            step_y=GRID_STEP_Y,
            clearance_units=DEFAULT_CLEARANCE,
        )
    grid = _require_mapping(raw, field_name="grid")
    return LayoutGridSpec(
        origin_x=_grid_int(grid, "origin_x", DEFAULT_ORIGIN_X),
        origin_y=_grid_int(grid, "origin_y", DEFAULT_ORIGIN_Y),
        step_x=_grid_int(grid, "step_x", GRID_STEP_X),
        step_y=_grid_int(grid, "step_y", GRID_STEP_Y),
        clearance_units=_grid_int(grid, "clearance_units", DEFAULT_CLEARANCE),
    )


def _infer_placement_mode(raw: dict[str, object]) -> str:
    explicit = raw.get("placement")
    if explicit is not None:
        if not isinstance(explicit, str) or explicit not in _SUPPORTED_PLACEMENT_MODES:
            allowed = ", ".join(sorted(_SUPPORTED_PLACEMENT_MODES))
            raise ValidationError(f"components[].placement must be one of: {allowed}.")
        return explicit
    if raw.get("position_x") is not None or raw.get("position_y") is not None:
        return "absolute"
    if raw.get("grid_column") is not None or raw.get("grid_row") is not None:
        return "grid"
    return "auto"


def _parse_component(raw: object, *, index: int) -> LayoutComponentSpec:
    if not isinstance(raw, dict):
        raise ValidationError(f"components[{index}] must be a JSON object.")
    kind = raw.get("component_kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValidationError(f"components[{index}].component_kind is required.")
    reference = raw.get("reference")
    if reference is not None and (not isinstance(reference, str) or not reference.strip()):
        raise ValidationError(f"components[{index}].reference must be a non-empty string.")
    net_name = raw.get("net_name")
    if net_name is not None and not isinstance(net_name, str):
        raise ValidationError(f"components[{index}].net_name must be a string.")
    placement = _infer_placement_mode(raw)
    position_x = _optional_int(raw.get("position_x"), field_name=f"components[{index}].position_x")
    position_y = _optional_int(raw.get("position_y"), field_name=f"components[{index}].position_y")
    grid_column = _optional_int(
        raw.get("grid_column"),
        field_name=f"components[{index}].grid_column",
    )
    grid_row = _optional_int(raw.get("grid_row"), field_name=f"components[{index}].grid_row")
    rotation = raw.get("rotation_degrees", 0)
    if isinstance(rotation, bool) or not isinstance(rotation, int):
        raise ValidationError(f"components[{index}].rotation_degrees must be an integer.")
    if rotation % 45 != 0:
        raise ValidationError(f"components[{index}].rotation_degrees must be a multiple of 45.")
    if placement == "absolute" and (position_x is None or position_y is None):
        raise ValidationError(
            f"components[{index}] with placement='absolute' requires position_x and position_y."
        )
    if placement == "grid" and grid_column is None:
        raise ValidationError(f"components[{index}] with placement='grid' requires grid_column.")
    value = raw.get("value")
    normalized_kind = kind.strip().lower()
    if normalized_kind != "ground" and value is None:
        raise ValidationError(f"components[{index}] requires value for kind {kind!r}.")
    return LayoutComponentSpec(
        reference=str(reference).strip() if isinstance(reference, str) else None,
        component_kind=normalized_kind,
        value=value,
        net_name=str(net_name).strip() if isinstance(net_name, str) else None,
        placement=placement,
        position_x=position_x,
        position_y=position_y,
        grid_column=grid_column,
        grid_row=grid_row if grid_row is not None else 0,
        rotation_degrees=rotation,
    )


def parse_layout_spec_document(raw: object) -> SchematicLayoutSpec:
    """Validate and normalize one layout specification mapping."""

    document = _require_mapping(raw, field_name="layout spec")
    schema_version = document.get("schema_version")
    if schema_version != LAYOUT_SPEC_SCHEMA_VERSION:
        raise ValidationError(
            f"Unsupported layout spec schema_version {schema_version!r}; "
            f"expected {LAYOUT_SPEC_SCHEMA_VERSION}."
        )
    schematic_path = document.get("schematic_path")
    if schematic_path is not None and not isinstance(schematic_path, str):
        raise ValidationError("schematic_path must be a string when provided.")
    components_raw = document.get("components")
    if not isinstance(components_raw, list) or not components_raw:
        raise ValidationError("components must be a non-empty array.")
    notes_raw = document.get("notes")
    notes: tuple[str, ...]
    if notes_raw is None:
        notes = ()
    elif isinstance(notes_raw, list):
        notes = tuple(str(item) for item in notes_raw)
    else:
        raise ValidationError("notes must be an array of strings when provided.")
    components = tuple(
        _parse_component(item, index=index) for index, item in enumerate(components_raw)
    )
    return SchematicLayoutSpec(
        schema_version=LAYOUT_SPEC_SCHEMA_VERSION,
        schematic_path=str(schematic_path) if isinstance(schematic_path, str) else None,
        grid=_parse_grid(document.get("grid")),
        components=components,
        notes=notes,
    )


def load_layout_spec_file(
    spec_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[Path, SchematicLayoutSpec]:
    """Read and validate one workspace-local JSON layout specification."""

    resolved_path = validate_existing_file(
        spec_path,
        workspace_root=workspace_root,
        suffixes=(".json",),
    )
    raw = json.loads(resolved_path.read_text(encoding="utf-8"))
    return resolved_path, parse_layout_spec_document(raw)


def resolve_layout_component_placement(
    entry: LayoutComponentSpec,
    *,
    grid: LayoutGridSpec,
    placed_components: tuple[PlacedComponent, ...],
) -> tuple[int, int]:
    """Resolve one layout row to schematic coordinates."""

    if entry.placement == "absolute":
        assert entry.position_x is not None
        assert entry.position_y is not None
        return entry.position_x, entry.position_y
    if entry.placement == "grid":
        assert entry.grid_column is not None
        assert entry.grid_row is not None
        return (
            grid.origin_x + entry.grid_column * grid.step_x,
            grid.origin_y + entry.grid_row * grid.step_y,
        )
    position_x, position_y, _notes = suggest_next_component_placement(
        component_kind=entry.component_kind,
        placed_components=placed_components,
        origin_x=grid.origin_x,
        origin_y=grid.origin_y,
        grid_step_x=grid.step_x,
        grid_step_y=grid.step_y,
        clearance_units=grid.clearance_units,
    )
    return position_x, position_y


def resolve_layout_placements(
    spec: SchematicLayoutSpec,
    *,
    placed_components: tuple[PlacedComponent, ...],
) -> tuple[ResolvedLayoutPlacement, ...]:
    """Resolve every component row in order, simulating cumulative placement."""

    resolved: list[ResolvedLayoutPlacement] = []
    virtual_placed = list(placed_components)
    for entry in spec.components:
        position_x, position_y = resolve_layout_component_placement(
            entry,
            grid=spec.grid,
            placed_components=tuple(virtual_placed),
        )
        half_width, half_height = component_half_extents(entry.component_kind)
        if entry.reference is not None:
            virtual_placed.append(
                PlacedComponent(
                    reference=entry.reference,
                    kind=entry.component_kind,
                    position_x=position_x,
                    position_y=position_y,
                    half_width=half_width,
                    half_height=half_height,
                )
            )
        resolved.append(
            ResolvedLayoutPlacement(
                reference=entry.reference,
                component_kind=entry.component_kind,
                value=entry.value,
                net_name=entry.net_name,
                position_x=position_x,
                position_y=position_y,
                rotation_degrees=entry.rotation_degrees,
                placement=entry.placement,
            )
        )
    return tuple(resolved)


__all__ = [
    "LAYOUT_SPEC_SCHEMA_VERSION",
    "LayoutComponentSpec",
    "LayoutGridSpec",
    "ResolvedLayoutPlacement",
    "SchematicLayoutSpec",
    "example_layout_spec_document",
    "layout_spec_json_schema",
    "load_layout_spec_file",
    "parse_layout_spec_document",
    "resolve_layout_placements",
]
