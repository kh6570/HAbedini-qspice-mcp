"""Tests for scratch buck power-stage component kinds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.list_components import list_components

if TYPE_CHECKING:
    from pathlib import Path


def test_scratch_power_stage_component_kinds_insert(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "buck.qsch", workspace_root=tmp_path)
    schematic = created.output_path

    parts = (
        ("inductor", "L1", "50µ"),
        ("nmos", "M1", "BSC123N08NS3"),
        ("pmos", "M2", "PMOS"),
        ("behavioral", "B1", "V=V(PWM)"),
    )
    for index, (kind, reference, value) in enumerate(parts):
        add_component(
            schematic,
            workspace_root=tmp_path,
            component_kind=kind,
            reference=reference,
            value=value,
            position_x=index * 400,
            position_y=0,
        )

    catalog = list_components(schematic, workspace_root=tmp_path)
    references = {item.reference for item in catalog.components}
    assert references == {"L1", "M1", "M2", "B1"}
