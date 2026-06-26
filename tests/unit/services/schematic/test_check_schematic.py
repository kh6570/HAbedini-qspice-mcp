"""Tests for the ERC checks and the check_schematic service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic._connectivity import (
    ComponentConnection,
    ConnectivityModel,
    NetGroup,
    NetLabelConflict,
    PinConnection,
)
from qspice_mcp.services.schematic._erc import evaluate_schematic_connectivity
from qspice_mcp.services.schematic.check_schematic import check_schematic
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic

if TYPE_CHECKING:
    from pathlib import Path


def _pin(reference: str, pin: str, net: str) -> PinConnection:
    return PinConnection(reference=reference, pin=pin, net=net, point=(0, 0))


def test_evaluate_flags_missing_ground() -> None:
    model = ConnectivityModel(
        node_count=1,
        nets=(NetGroup(name="N001", members=(_pin("R1", "1", "N001"),), labeled=False),),
        components=(
            ComponentConnection(
                reference="R1",
                kind="R",
                symbol="R",
                value="1k",
                description=None,
                pins=("1", "2"),
            ),
        ),
        conflicts=(),
        ground_present=False,
    )

    report = evaluate_schematic_connectivity(model)

    codes = {finding.code for finding in report.findings}
    assert "missing_ground" in codes
    assert report.ok is False
    assert report.error_count >= 1


def test_evaluate_flags_duplicate_reference_and_conflicts() -> None:
    model = ConnectivityModel(
        node_count=1,
        nets=(
            NetGroup(
                name="0",
                members=(_pin("R1", "1", "0"), _pin("R1", "2", "0")),
                labeled=True,
            ),
        ),
        components=(
            ComponentConnection("R1", "R", "R", "1k", None, ("1", "2")),
            ComponentConnection("R1", "R", "R", "2k", None, ("1", "2")),
        ),
        conflicts=(NetLabelConflict(labels=("0", "VOUT"), references=("R1",)),),
        ground_present=True,
    )

    report = evaluate_schematic_connectivity(model)
    codes = {finding.code for finding in report.findings}
    assert "duplicate_reference" in codes
    assert "conflicting_net_labels" in codes


def test_evaluate_flags_floating_pin_and_missing_value() -> None:
    model = ConnectivityModel(
        node_count=2,
        nets=(
            NetGroup(name="0", members=(_pin("R1", "2", "0"),), labeled=True),
            NetGroup(name="N002", members=(_pin("R1", "1", "N002"),), labeled=False),
        ),
        components=(ComponentConnection("R1", "R", "R", None, None, ("1", "2")),),
        conflicts=(),
        ground_present=True,
    )

    report = evaluate_schematic_connectivity(model)
    codes = {finding.code for finding in report.findings}
    assert "floating_pin" in codes
    assert "missing_value" in codes
    assert report.warning_count >= 2


def test_evaluate_ignores_value_for_ground_symbol() -> None:
    model = ConnectivityModel(
        node_count=1,
        nets=(NetGroup(name="0", members=(_pin("R1", "2", "0"),), labeled=True),),
        components=(ComponentConnection(None, "GROUND", "GND", None, None, ()),),
        conflicts=(),
        ground_present=True,
    )

    report = evaluate_schematic_connectivity(model)
    assert all(finding.code != "missing_value" for finding in report.findings)


def test_check_schematic_passes_on_starter(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)

    report = check_schematic(schematic, workspace_root=tmp_path)

    assert report.error_count == 0
    assert report.schematic_path == schematic.resolve(strict=False)
