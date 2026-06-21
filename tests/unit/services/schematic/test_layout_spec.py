"""Tests for schematic layout specification v1 parsing and application."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.schematic._layout_spec import (
    LAYOUT_SPEC_SCHEMA_VERSION,
    parse_layout_spec_document,
    resolve_layout_placements,
)
from qspice_mcp.services.schematic.apply_schematic_layout_spec import (
    apply_schematic_layout_spec,
)
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.describe_schematic_layout_spec import (
    describe_schematic_layout_spec,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_describe_schematic_layout_spec_returns_v1_example() -> None:
    description = describe_schematic_layout_spec()

    assert description.schema_version == LAYOUT_SPEC_SCHEMA_VERSION
    assert description.placement_modes == ("auto", "grid", "absolute")
    assert description.example_document["schema_version"] == LAYOUT_SPEC_SCHEMA_VERSION
    assert len(description.example_document["components"]) >= 1


def test_parse_layout_spec_rejects_unsupported_schema_version() -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        parse_layout_spec_document({"schema_version": 99, "components": []})


def test_resolve_layout_placements_auto_avoids_overlap() -> None:
    spec = parse_layout_spec_document(
        {
            "schema_version": 1,
            "components": [
                {
                    "reference": "L1",
                    "component_kind": "inductor",
                    "value": "50µ",
                    "placement": "auto",
                },
                {
                    "reference": "M1",
                    "component_kind": "nmos",
                    "value": "NMOS",
                    "placement": "auto",
                },
            ],
        }
    )
    resolved = resolve_layout_placements(spec, placed_components=())

    assert len(resolved) == 2
    first, second = resolved
    assert (first.position_x, first.position_y) != (second.position_x, second.position_y)


def test_resolve_layout_placements_grid_and_absolute() -> None:
    spec = parse_layout_spec_document(
        {
            "schema_version": 1,
            "grid": {
                "origin_x": 100,
                "origin_y": 200,
                "step_x": 50,
                "step_y": 60,
            },
            "components": [
                {
                    "reference": "R1",
                    "component_kind": "resistor",
                    "value": "1k",
                    "placement": "grid",
                    "grid_column": 2,
                    "grid_row": 1,
                },
                {
                    "reference": "C1",
                    "component_kind": "capacitor",
                    "value": "1µ",
                    "placement": "absolute",
                    "position_x": 900,
                    "position_y": 800,
                },
            ],
        }
    )
    resolved = resolve_layout_placements(spec, placed_components=())

    assert resolved[0].position_x == 100 + 2 * 50
    assert resolved[0].position_y == 200 + 1 * 60
    assert resolved[1].position_x == 900
    assert resolved[1].position_y == 800


def test_apply_schematic_layout_spec_places_components(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "stage.qsch", workspace_root=tmp_path)
    spec_path = tmp_path / "stage.v1.json"
    spec_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "components": [
                    {
                        "reference": "L1",
                        "component_kind": "inductor",
                        "value": "50µ",
                        "placement": "auto",
                    },
                    {
                        "reference": "M1",
                        "component_kind": "nmos",
                        "value": "NMOS",
                        "placement": "auto",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = apply_schematic_layout_spec(
        created.output_path,
        spec_path,
        workspace_root=tmp_path,
    )

    assert result.applied_count == 2
    assert result.skipped_existing_count == 0
    assert len(result.components) == 2
    assert result.components[0].reference == "L1"
    assert result.components[1].reference == "M1"
    assert (result.components[0].position_x, result.components[0].position_y) != (
        result.components[1].position_x,
        result.components[1].position_y,
    )


def test_apply_schematic_layout_spec_skip_existing(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "skip.qsch", workspace_root=tmp_path)
    spec_path = tmp_path / "skip.v1.json"
    spec_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "components": [
                    {
                        "reference": "L1",
                        "component_kind": "inductor",
                        "value": "50µ",
                        "placement": "auto",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    first = apply_schematic_layout_spec(
        created.output_path,
        spec_path,
        workspace_root=tmp_path,
    )
    second = apply_schematic_layout_spec(
        first.output_path,
        spec_path,
        workspace_root=tmp_path,
        skip_existing=True,
    )

    assert first.applied_count == 1
    assert second.applied_count == 0
    assert second.skipped_existing_count == 1
    assert second.components[0].skipped_existing is True
