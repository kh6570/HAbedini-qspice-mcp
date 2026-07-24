"""Tests for the `.meas` preparation service."""

from __future__ import annotations

import pytest

from qspice_mcp.services.simulation.prepare_meas import prepare_meas


def _write_netlist(tmp_path):
    netlist = tmp_path / "smps.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    return netlist


def test_prepare_meas_fra_statement(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)
    staged = tmp_path / "smps-meas.net"

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="fra",
        name="XOVER",
        frequency="12k",
        input_expression="V(inj)",
        output_expression="V(out)",
        output_path=staged,
    )

    assert prepared.kind == "fra"
    assert prepared.instruction == ".meas XOVER fra 12k V(inj) V(out)"
    assert staged.read_text(encoding="utf-8") == (
        "* base\n.meas XOVER fra 12k V(inj) V(out)\n.end\n"
    )


def test_prepare_meas_find_at_statement(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="find_at",
        name="POWER",
        expression="V(x)*I(V1)",
        at="100u",
        output_path=tmp_path / "smps-meas.net",
    )

    assert prepared.instruction == ".meas POWER find V(x)*I(V1) at 100u"


def test_prepare_meas_avg_with_window(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="avg",
        name="VRIPPLE",
        statistic="pp",
        expression="V(out)",
        start="1m",
        stop="2m",
        output_path=tmp_path / "smps-meas.net",
    )

    assert prepared.instruction == ".meas VRIPPLE pp V(out) from 1m to 2m"


def test_prepare_meas_trig_targ_statement(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="trig_targ",
        name="TSETTLE",
        trig="V(out)=1",
        targ="V(out)=4.9",
        output_path=tmp_path / "smps-meas.net",
    )

    assert prepared.instruction == ".meas TSETTLE trig V(out)=1 targ V(out)=4.9"


def test_prepare_meas_four_statement(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="four",
        name="H3",
        frequency="150",
        expression="V(out)",
        output_path=tmp_path / "smps-meas.net",
    )

    assert prepared.instruction == ".meas H3 four 150 V(out)"


def test_prepare_meas_raw_statement_requires_meas_prefix(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    prepared = prepare_meas(
        netlist,
        workspace_root=tmp_path,
        kind="raw",
        instruction=".meas VMAX max V(out)",
        output_path=tmp_path / "smps-meas.net",
    )
    assert prepared.instruction == ".meas VMAX max V(out)"

    with pytest.raises(ValueError, match="must start with"):
        prepare_meas(
            netlist,
            workspace_root=tmp_path,
            kind="raw",
            instruction=".tran 1u 1m",
        )


def test_prepare_meas_validates_kind_and_required_fields(tmp_path) -> None:
    netlist = _write_netlist(tmp_path)

    with pytest.raises(ValueError, match="kind must be one of"):
        prepare_meas(netlist, workspace_root=tmp_path, kind="derivative")

    with pytest.raises(ValueError, match="frequency is required"):
        prepare_meas(
            netlist,
            workspace_root=tmp_path,
            kind="fra",
            name="XOVER",
            input_expression="V(inj)",
            output_expression="V(out)",
        )

    with pytest.raises(ValueError, match="start and stop must be provided together"):
        prepare_meas(
            netlist,
            workspace_root=tmp_path,
            kind="avg",
            name="VAVG",
            expression="V(out)",
            start="1m",
        )

    with pytest.raises(ValueError, match="must not contain whitespace"):
        prepare_meas(
            netlist,
            workspace_root=tmp_path,
            kind="four",
            name="bad name",
            frequency="150",
            expression="V(out)",
        )
