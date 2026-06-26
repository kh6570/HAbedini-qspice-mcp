"""Tests for the read_net_connectivity service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.read_net_connectivity import read_net_connectivity

if TYPE_CHECKING:
    from pathlib import Path


def test_read_net_connectivity_reports_nets_and_ground(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")

    report = read_net_connectivity(schematic, workspace_root=tmp_path)

    assert report.schematic_path == schematic.resolve(strict=False)
    assert report.component_count == 2
    assert report.ground_present is True
    net_names = {net.net for net in report.nets}
    assert "0" in net_names
    assert "VIN" in net_names

    vin_net = next(net for net in report.nets if net.net == "VIN")
    references = {pin.reference for pin in vin_net.pins}
    assert references == {"V1", "R1"}
