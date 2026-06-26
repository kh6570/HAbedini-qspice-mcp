"""Tests for schematic layout helpers and suggest_component_placement."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.schematic._layout import (
    GRID_STEP_X,
    PlacedComponent,
    suggest_next_component_placement,
)
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.suggest_component_placement import (
    suggest_component_placement,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_suggest_next_component_placement_avoids_overlap() -> None:
    placed = (
        PlacedComponent(
            reference="R1",
            kind="resistor",
            position_x=400,
            position_y=400,
            half_width=160,
            half_height=90,
        ),
    )
    position_x, position_y, _notes = suggest_next_component_placement(
        component_kind="capacitor",
        placed_components=placed,
        origin_x=400,
        origin_y=400,
        grid_step_x=GRID_STEP_X,
        grid_step_y=400,
    )
    assert (position_x, position_y) != (400, 400)
    assert position_x > 400


def test_suggest_component_placement_on_blank_schematic(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "layout.qsch", workspace_root=tmp_path)
    suggestion = suggest_component_placement(
        created.output_path,
        workspace_root=tmp_path,
        component_kind="inductor",
    )
    assert suggestion.rotation_degrees == 0
    assert suggestion.position_x >= 400
    assert suggestion.existing_component_count == 0


def test_add_component_auto_place_avoids_stacked_origin(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "buck.qsch", workspace_root=tmp_path)
    schematic = created.output_path

    first = add_component(
        schematic,
        workspace_root=tmp_path,
        component_kind="inductor",
        reference="L1",
        value="50µ",
        auto_place=True,
    )
    second = add_component(
        schematic,
        workspace_root=tmp_path,
        component_kind="nmos",
        reference="M1",
        value="NMOS",
        auto_place=True,
    )

    assert (first.position_x, first.position_y) != (second.position_x, second.position_y)
    assert (
        abs(first.position_x - second.position_x) >= 900
        or abs(first.position_y - second.position_y) >= 500
    )
    assert first.rotation_degrees == 0
    assert second.rotation_degrees == 0


def test_suggest_component_placement_raises_when_grid_full(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = create_schematic(tmp_path / "full.qsch", workspace_root=tmp_path)

    def _dense_placements(
        *_args: object,
        **_kwargs: object,
    ) -> tuple[object, tuple[PlacedComponent, ...]]:
        return created.output_path, tuple(
            PlacedComponent(
                reference=f"R{index}",
                kind="resistor",
                position_x=400 + (index % 2) * 50,
                position_y=400 + (index // 2) * 50,
                half_width=300,
                half_height=300,
            )
            for index in range(20)
        )

    monkeypatch.setattr(
        "qspice_mcp.services.schematic.suggest_component_placement.load_placed_components",
        _dense_placements,
    )

    with pytest.raises(ValidationError, match="No collision-free placement"):
        suggest_component_placement(
            created.output_path,
            workspace_root=tmp_path,
            component_kind="resistor",
            max_columns=1,
            max_rows=1,
        )
