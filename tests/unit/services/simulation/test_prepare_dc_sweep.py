"""Tests for the `.dc` preparation service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_dc_sweep import prepare_dc_sweep

prepare_dc_module = importlib.import_module("qspice_mcp.services.simulation.prepare_dc_sweep")


def test_prepare_dc_sweep_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "divider.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "divider-dc.qsch"

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert instruction == ".dc V1 0 5 0.1"
        assert Path(output_path or staged) == staged
        staged.write_text("schematic", encoding="utf-8")
        return InstructionAdd(
            schematic_path=schematic.resolve(strict=False),
            output_path=staged.resolve(strict=False),
            instruction=instruction,
        )

    monkeypatch.setattr(prepare_dc_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_dc_sweep(
        schematic,
        workspace_root=tmp_path,
        source="V1",
        start="0",
        stop="5",
        step="0.1",
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.instruction == ".dc V1 0 5 0.1"


def test_prepare_dc_sweep_appends_to_netlist_copy(tmp_path: Path) -> None:
    netlist = tmp_path / "divider.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "artifacts" / "divider-dc.net"

    prepared = prepare_dc_sweep(
        netlist,
        workspace_root=tmp_path,
        source="V1",
        start="0",
        stop="5",
        step="0.1",
        output_path=staged,
    )

    assert prepared.source_kind == "netlist"
    assert staged.read_text(encoding="utf-8") == "* base\n.dc V1 0 5 0.1\n.end\n"


def test_prepare_dc_sweep_decade_mode(tmp_path: Path) -> None:
    netlist = tmp_path / "divider.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    prepared = prepare_dc_sweep(
        netlist,
        workspace_root=tmp_path,
        source="I1",
        sweep_mode="dec",
        start="1u",
        stop="1m",
        step="10",
        output_path=tmp_path / "divider-dc.net",
    )

    assert prepared.instruction == ".dc dec I1 1u 1m 10"


def test_prepare_dc_sweep_list_mode(tmp_path: Path) -> None:
    netlist = tmp_path / "divider.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    prepared = prepare_dc_sweep(
        netlist,
        workspace_root=tmp_path,
        source="V1",
        sweep_mode="list",
        list_values=["0", "2.5", "5"],
        output_path=tmp_path / "divider-dc.net",
    )

    assert prepared.instruction == ".dc V1 list 0 2.5 5"


def test_prepare_dc_sweep_two_dimensions(tmp_path: Path) -> None:
    netlist = tmp_path / "curve.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    prepared = prepare_dc_sweep(
        netlist,
        workspace_root=tmp_path,
        source="VDS",
        start="0",
        stop="5",
        step="0.1",
        second_source="VGS",
        second_sweep_mode="list",
        second_list_values=["1", "2", "3"],
        output_path=tmp_path / "curve-dc.net",
    )

    assert prepared.instruction == ".dc VDS 0 5 0.1 VGS list 1 2 3"


def test_prepare_dc_sweep_validates_missing_range(tmp_path: Path) -> None:
    netlist = tmp_path / "divider.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    with pytest.raises(ValueError, match="requires start, stop, and step"):
        prepare_dc_sweep(netlist, workspace_root=tmp_path, source="V1")

    with pytest.raises(ValueError, match="list sweep requires at least one value"):
        prepare_dc_sweep(netlist, workspace_root=tmp_path, source="V1", sweep_mode="list")
