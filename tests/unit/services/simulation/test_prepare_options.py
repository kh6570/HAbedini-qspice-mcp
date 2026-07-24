"""Tests for the `.options` preparation service."""

from __future__ import annotations

import pytest

from qspice_mcp.services.simulation.prepare_options import prepare_options


def test_prepare_options_renders_convergence_options(tmp_path) -> None:
    netlist = tmp_path / "tank.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "tank-options.net"

    prepared = prepare_options(
        netlist,
        workspace_root=tmp_path,
        cshunt="1e-12",
        method="gear",
        output_path=staged,
    )

    assert prepared.instruction == ".options cshunt=1e-12 method=gear"
    assert staged.read_text(encoding="utf-8") == (
        "* base\n.options cshunt=1e-12 method=gear\n.end\n"
    )


def test_prepare_options_renders_bode_and_flag_options(tmp_path) -> None:
    netlist = tmp_path / "loop.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    prepared = prepare_options(
        netlist,
        workspace_root=tmp_path,
        boderef="vref",
        bodeampfreq="0",
        savepowers=True,
        output_path=tmp_path / "loop-options.net",
    )

    assert prepared.instruction == ".options boderef=vref bodeampfreq=0 savepowers=1"


def test_prepare_options_requires_at_least_one_option(tmp_path) -> None:
    netlist = tmp_path / "tank.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    with pytest.raises(ValueError, match="At least one simulator option"):
        prepare_options(netlist, workspace_root=tmp_path)


def test_prepare_options_rejects_unknown_method(tmp_path) -> None:
    netlist = tmp_path / "tank.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    with pytest.raises(ValueError, match="method must be one of"):
        prepare_options(netlist, workspace_root=tmp_path, method="euler")
