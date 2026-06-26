"""Tests for the netlist ERC checks and the check_netlist service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic._erc import evaluate_netlist
from qspice_mcp.services.schematic.check_netlist import check_netlist

if TYPE_CHECKING:
    from pathlib import Path

_GOOD_NETLIST = """* demo
V1 VIN 0 PULSE(0 5 0 1n 1n 5u 10u)
R1 VIN OUT 100
C1 OUT 0 1u
.tran 100n 100u
.end
"""

_MISSING_GROUND = """* demo
V1 VIN OUT 5
R1 VIN OUT 100
.op
.end
"""

_DUPLICATE = """* demo
R1 VIN 0 100
R1 OUT 0 200
.end
"""


def test_evaluate_netlist_accepts_grounded_netlist() -> None:
    report = evaluate_netlist(_GOOD_NETLIST)
    assert report.ok is True
    assert report.error_count == 0


def test_evaluate_netlist_flags_missing_ground() -> None:
    report = evaluate_netlist(_MISSING_GROUND)
    codes = {finding.code for finding in report.findings}
    assert "missing_ground" in codes
    assert report.ok is False


def test_evaluate_netlist_flags_duplicate_reference() -> None:
    report = evaluate_netlist(_DUPLICATE)
    codes = {finding.code for finding in report.findings}
    assert "duplicate_reference" in codes


def test_evaluate_netlist_flags_single_connection_node() -> None:
    report = evaluate_netlist("* demo\nR1 A 0 100\nR2 0 0 200\n.end\n")
    codes = {finding.code for finding in report.findings}
    assert "single_connection_node" in codes


def test_check_netlist_service_reads_file(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text(_GOOD_NETLIST, encoding="utf-8")

    report = check_netlist(netlist, workspace_root=tmp_path)

    assert report.ok is True
    assert report.netlist_path == netlist.resolve(strict=False)
