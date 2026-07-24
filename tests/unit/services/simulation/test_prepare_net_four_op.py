"""Tests for the `.net`, `.four`, and `.op` preparation services."""

from __future__ import annotations

import pytest

from qspice_mcp.services.simulation.prepare_four import prepare_four
from qspice_mcp.services.simulation.prepare_net import prepare_net
from qspice_mcp.services.simulation.prepare_op import prepare_op


def _write_netlist(tmp_path, name: str = "circuit.net"):
    netlist = tmp_path / name
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    return netlist


def test_prepare_net_one_port(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)
    staged = tmp_path / "circuit-net.net"

    prepared = prepare_net(
        netlist,
        workspace_root=tmp_path,
        input_source="V1",
        output_path=staged,
    )

    assert prepared.instruction == ".net V1"
    assert staged.read_text(encoding="utf-8") == "* base\n.net V1\n.end\n"
    assert any("S11" in warning for warning in prepared.warnings)
    assert any("`.ac`" in warning for warning in prepared.warnings)


def test_prepare_net_two_port(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_net(
        netlist,
        workspace_root=tmp_path,
        input_source="V1",
        output_resistor="Rload",
        output_path=tmp_path / "circuit-net.net",
    )

    assert prepared.instruction == ".net Rload V1"
    assert any("Two-port" in warning for warning in prepared.warnings)


def test_prepare_net_rejects_blank_source(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    with pytest.raises(ValueError, match="input_source"):
        prepare_net(netlist, workspace_root=tmp_path, input_source="  ")


def test_prepare_four_with_harmonics_and_periods(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)
    staged = tmp_path / "circuit-four.net"

    prepared = prepare_four(
        netlist,
        workspace_root=tmp_path,
        frequency="50",
        harmonics=9,
        periods=4,
        expressions=["V(out)", "I(L1)"],
        output_path=staged,
    )

    assert prepared.instruction == ".four 50 9 4 V(out) I(L1)"
    assert staged.read_text(encoding="utf-8") == "* base\n.four 50 9 4 V(out) I(L1)\n.end\n"


def test_prepare_four_periods_requires_harmonics(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    with pytest.raises(ValueError, match="harmonics must be provided"):
        prepare_four(
            netlist,
            workspace_root=tmp_path,
            frequency="50",
            periods=4,
            expressions=["V(out)"],
        )


def test_prepare_four_requires_expressions(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    with pytest.raises(ValueError, match="expressions"):
        prepare_four(netlist, workspace_root=tmp_path, frequency="50", expressions=[])


def test_prepare_op_appends_directive(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)
    staged = tmp_path / "circuit-op.net"

    prepared = prepare_op(netlist, workspace_root=tmp_path, output_path=staged)

    assert prepared.instruction == ".op"
    assert staged.read_text(encoding="utf-8") == "* base\n.op\n.end\n"
