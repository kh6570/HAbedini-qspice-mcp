"""Tests for the move_component_preserving_connections service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.move_component_preserving_connections import (
    move_component_preserving_connections,
)
from qspice_mcp.services.schematic.read_net_connectivity import read_net_connectivity

if TYPE_CHECKING:
    from pathlib import Path


def test_move_component_follows_attached_connections(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")
    moved = tmp_path / "moved.qsch"

    result = move_component_preserving_connections(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        position_x=1600,
        position_y=1200,
        output_path=moved,
    )

    assert result.position_x == 1600
    assert result.position_y == 1200
    assert result.rewired_endpoints >= 1

    report = read_net_connectivity(moved, workspace_root=tmp_path)
    vin_net = next(net for net in report.nets if net.net == "VIN")
    references = {pin.reference for pin in vin_net.pins}
    assert references == {"V1", "R1"}
    assert report.ground_present is True


def test_move_component_requires_a_change(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)

    with pytest.raises(ValueError, match="at least one"):
        move_component_preserving_connections(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            output_path=tmp_path / "noop.qsch",
        )
