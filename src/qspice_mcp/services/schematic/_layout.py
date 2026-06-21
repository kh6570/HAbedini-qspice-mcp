"""Grid placement and collision helpers for schematic authoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.services._backends.clean_room_schematic import (
    inspect_supported_schematic_components,
)
from qspice_mcp.services._backends.schematic_editor import (
    normalize_component_position,
    open_schematic_editor,
)
from qspice_mcp.services._shared.paths import validate_existing_file

if TYPE_CHECKING:
    from pathlib import Path

GRID_STEP_X = 400
GRID_STEP_Y = 400
DEFAULT_CLEARANCE = 80
# Extra margin so refdes/value text (offset ~100,150 from anchor) does not overlap.
_TEXT_LABEL_MARGIN_X = 120
_TEXT_LABEL_MARGIN_Y = 100
DEFAULT_ORIGIN_X = 400
DEFAULT_ORIGIN_Y = 400
DEFAULT_MAX_COLUMNS = 12
DEFAULT_MAX_ROWS = 16

# Conservative half-extents (schematic units) for collision boxes around anchors.
_COMPONENT_HALF_EXTENTS: dict[str, tuple[int, int]] = {
    "resistor": (160, 90),
    "capacitor": (130, 110),
    "diode": (160, 100),
    "voltage_source": (160, 220),
    "inductor": (190, 130),
    "behavioral": (170, 110),
    "nmos": (220, 260),
    "pmos": (220, 260),
    "ground": (90, 90),
    "dll_block": (360, 360),
}


@dataclass(frozen=True, slots=True)
class PlacedComponent:
    """One component anchor and collision footprint."""

    reference: str
    kind: str
    position_x: int
    position_y: int
    half_width: int
    half_height: int


@dataclass(frozen=True, slots=True)
class ComponentPlacementSuggestion:
    """Suggested coordinates for the next readable component placement."""

    schematic_path: Path
    component_kind: str
    position_x: int
    position_y: int
    rotation_degrees: int
    grid_step_x: int
    grid_step_y: int
    clearance_units: int
    existing_component_count: int
    notes: tuple[str, ...]


def component_half_extents(component_kind: str) -> tuple[int, int]:
    normalized = component_kind.strip().lower()
    aliases = {
        "r": "resistor",
        "c": "capacitor",
        "d": "diode",
        "v": "voltage_source",
        "l": "inductor",
        "b": "behavioral",
        "mn": "nmos",
        "n": "nmos",
        "mp": "pmos",
        "p": "pmos",
        "gnd": "ground",
        "x": "dll_block",
    }
    resolved = aliases.get(normalized, normalized)
    half_width, half_height = _COMPONENT_HALF_EXTENTS.get(resolved, (180, 150))
    return (
        half_width + _TEXT_LABEL_MARGIN_X,
        half_height + _TEXT_LABEL_MARGIN_Y,
    )


def _collides(
    *,
    position_x: int,
    position_y: int,
    half_width: int,
    half_height: int,
    placed: PlacedComponent,
    clearance: int,
) -> bool:
    return (
        abs(position_x - placed.position_x)
        < half_width + placed.half_width + clearance
        and abs(position_y - placed.position_y)
        < half_height + placed.half_height + clearance
    )


def load_placed_components(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[Path, tuple[PlacedComponent, ...]]:
    """Return normalized placement footprints for components already on the schematic."""

    resolved_workspace = workspace_root.resolve(strict=False)
    placed: list[PlacedComponent] = []
    try:
        editor, resolved_path, _ = open_schematic_editor(
            schematic_path,
            workspace_root=resolved_workspace,
        )
    except BackendUnavailableError:
        resolved_path = validate_existing_file(
            schematic_path,
            workspace_root=resolved_workspace,
            suffixes=(".qsch",),
        )
        for item in inspect_supported_schematic_components(resolved_path):
            half_width, half_height = component_half_extents(item.kind)
            placed.append(
                PlacedComponent(
                    reference=item.reference,
                    kind=item.kind,
                    position_x=item.position_x,
                    position_y=item.position_y,
                    half_width=half_width,
                    half_height=half_height,
                )
            )
        return resolved_path, tuple(placed)

    for reference in editor.get_components(prefixes="*"):
        ref = str(reference)
        editor_component = editor.get_component(ref)
        attributes = dict(editor_component.attributes)
        kind = str(attributes.get("type") or ref[:1]).lower()
        position, rotation_raw = editor.get_component_position(ref)
        del rotation_raw
        position_x, position_y = normalize_component_position(position)
        half_width, half_height = component_half_extents(kind)
        placed.append(
            PlacedComponent(
                reference=ref,
                kind=kind,
                position_x=position_x,
                position_y=position_y,
                half_width=half_width,
                half_height=half_height,
            )
        )
    return resolved_path, tuple(placed)


def suggest_next_component_placement(
    *,
    component_kind: str,
    placed_components: tuple[PlacedComponent, ...],
    origin_x: int = DEFAULT_ORIGIN_X,
    origin_y: int = DEFAULT_ORIGIN_Y,
    grid_step_x: int = GRID_STEP_X,
    grid_step_y: int = GRID_STEP_Y,
    clearance_units: int = DEFAULT_CLEARANCE,
    max_columns: int = DEFAULT_MAX_COLUMNS,
    max_rows: int = DEFAULT_MAX_ROWS,
) -> tuple[int, int, tuple[str, ...]]:
    """Pick the first collision-free grid slot scanning left-to-right, then downward."""

    half_width, half_height = component_half_extents(component_kind)
    notes = (
        "Scanning left-to-right on each row, then the next row downward.",
        (
            "Default rotation is 0° so refdes/value text stays upright; "
            "rotate only when the topology requires it."
        ),
    )
    for row in range(max_rows):
        position_y = origin_y + row * grid_step_y
        for column in range(max_columns):
            position_x = origin_x + column * grid_step_x
            if any(
                _collides(
                    position_x=position_x,
                    position_y=position_y,
                    half_width=half_width,
                    half_height=half_height,
                    placed=item,
                    clearance=clearance_units,
                )
                for item in placed_components
            ):
                continue
            return position_x, position_y, notes

    raise ValidationError(
        "No collision-free placement found in the scanned grid region. "
        "Increase origin coordinates, widen the scan area, or move existing components "
        "with set_component_position."
    )


__all__ = [
    "DEFAULT_CLEARANCE",
    "DEFAULT_ORIGIN_X",
    "DEFAULT_ORIGIN_Y",
    "GRID_STEP_X",
    "GRID_STEP_Y",
    "ComponentPlacementSuggestion",
    "PlacedComponent",
    "component_half_extents",
    "load_placed_components",
    "suggest_next_component_placement",
]
