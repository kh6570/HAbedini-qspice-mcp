"""Suggest collision-free schematic coordinates for the next component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic._layout import (
    DEFAULT_CLEARANCE,
    DEFAULT_MAX_COLUMNS,
    DEFAULT_MAX_ROWS,
    DEFAULT_ORIGIN_X,
    DEFAULT_ORIGIN_Y,
    GRID_STEP_X,
    GRID_STEP_Y,
    ComponentPlacementSuggestion,
    load_placed_components,
    suggest_next_component_placement,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

SERVICE_SPEC = ServiceSpec(
    name="suggest_component_placement",
    title="Suggest Component Placement",
    summary=(
        "Suggest collision-free schematic coordinates for the next component "
        "using a readable left-to-right grid with upright (0°) rotation."
    ),
    phase="implemented",
    read_only=True,
)


def suggest_component_placement(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    component_kind: str,
    origin_x: int = DEFAULT_ORIGIN_X,
    origin_y: int = DEFAULT_ORIGIN_Y,
    grid_step_x: int = GRID_STEP_X,
    grid_step_y: int = GRID_STEP_Y,
    clearance_units: int = DEFAULT_CLEARANCE,
    max_columns: int = DEFAULT_MAX_COLUMNS,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> ComponentPlacementSuggestion:
    """Return the next readable grid placement that avoids overlapping existing parts."""

    resolved_path, placed = load_placed_components(
        schematic_path,
        workspace_root=workspace_root,
    )
    position_x, position_y, notes = suggest_next_component_placement(
        component_kind=component_kind,
        placed_components=placed,
        origin_x=origin_x,
        origin_y=origin_y,
        grid_step_x=grid_step_x,
        grid_step_y=grid_step_y,
        clearance_units=clearance_units,
        max_columns=max_columns,
        max_rows=max_rows,
    )
    return ComponentPlacementSuggestion(
        schematic_path=resolved_path,
        component_kind=component_kind.strip().lower(),
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=0,
        grid_step_x=grid_step_x,
        grid_step_y=grid_step_y,
        clearance_units=clearance_units,
        existing_component_count=len(placed),
        notes=notes,
    )


__all__ = ["SERVICE_SPEC", "ComponentPlacementSuggestion", "suggest_component_placement"]
