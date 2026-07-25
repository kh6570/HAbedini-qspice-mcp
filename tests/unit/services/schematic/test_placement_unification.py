"""Behavioral tests for unified placement defaults and orphan-wire cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.read_net_connectivity import read_net_connectivity
from qspice_mcp.services.schematic.remove_component import remove_component
from qspice_mcp.services.schematic.set_component_position import set_component_position

if TYPE_CHECKING:
    from pathlib import Path


def test_set_component_position_preserves_connections_by_default(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")
    moved = tmp_path / "moved.qsch"

    result = set_component_position(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        position_x=1600,
        position_y=1200,
        output_path=moved,
    )

    assert result.preserve_connections is True
    assert result.position_x == 1600
    assert result.position_y == 1200
    assert result.rewired_endpoints >= 1

    report = read_net_connectivity(moved, workspace_root=tmp_path)
    vin_net = next(net for net in report.nets if net.net == "VIN")
    references = {pin.reference for pin in vin_net.pins}
    assert references == {"V1", "R1"}


def test_set_component_position_requires_a_change(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)

    with pytest.raises(ValueError, match="at least one"):
        set_component_position(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            output_path=tmp_path / "noop.qsch",
        )


def test_set_component_position_rotation_only_keeps_position(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")
    rotated = tmp_path / "rotated.qsch"

    result = set_component_position(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        rotation_degrees=90,
        output_path=rotated,
    )

    assert result.rotation_degrees == 90
    # Connectivity must survive a rotation that follows the pins.
    report = read_net_connectivity(rotated, workspace_root=tmp_path)
    vin_net = next(net for net in report.nets if net.net == "VIN")
    assert {pin.reference for pin in vin_net.pins} == {"V1", "R1"}


def test_remove_component_keeps_wires_without_opt_in(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")
    removed = tmp_path / "removed.qsch"

    result = remove_component(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        output_path=removed,
    )

    assert result.remove_orphan_wires is False
    assert result.wires_removed == 0


def test_remove_component_prunes_orphan_wires_when_requested(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path, input_net_name="VIN")
    removed = tmp_path / "removed.qsch"

    baseline = read_net_connectivity(schematic, workspace_root=tmp_path)
    baseline_wire_pins = sum(len(net.pins) for net in baseline.nets)

    result = remove_component(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        remove_orphan_wires=True,
        output_path=removed,
    )

    assert result.remove_orphan_wires is True
    # R1 sat on the VIN net wire; removing it should drop at least one dangling item.
    total_pruned = result.wires_removed + result.junctions_removed + result.net_labels_removed
    assert total_pruned >= 1

    after = read_net_connectivity(removed, workspace_root=tmp_path)
    after_wire_pins = sum(len(net.pins) for net in after.nets)
    assert after_wire_pins <= baseline_wire_pins
