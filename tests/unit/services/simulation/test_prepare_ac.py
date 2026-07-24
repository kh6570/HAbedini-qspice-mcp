"""Tests for the `.ac` preparation service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_ac import prepare_ac

prepare_ac_module = importlib.import_module("qspice_mcp.services.simulation.prepare_ac")


def test_prepare_ac_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "filter.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "filter-ac.qsch"

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert instruction == ".ac dec 100 1 1Meg"
        assert Path(output_path or staged) == staged
        staged.write_text("schematic", encoding="utf-8")
        return InstructionAdd(
            schematic_path=schematic.resolve(strict=False),
            output_path=staged.resolve(strict=False),
            instruction=instruction,
        )

    monkeypatch.setattr(prepare_ac_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_ac(
        schematic,
        workspace_root=tmp_path,
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.instruction == ".ac dec 100 1 1Meg"


def test_prepare_ac_appends_to_netlist_copy(tmp_path: Path) -> None:
    netlist = tmp_path / "filter.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "artifacts" / "filter-ac.net"

    prepared = prepare_ac(
        netlist,
        workspace_root=tmp_path,
        sweep_type="oct",
        points="20",
        start="10",
        stop="100k",
        output_path=staged,
    )

    assert prepared.source_kind == "netlist"
    assert staged.read_text(encoding="utf-8") == "* base\n.ac oct 20 10 100k\n.end\n"


def test_prepare_ac_list_sweep(tmp_path: Path) -> None:
    netlist = tmp_path / "filter.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    prepared = prepare_ac(
        netlist,
        workspace_root=tmp_path,
        sweep_type="list",
        frequencies=["1k", "10k", "100k"],
        output_path=tmp_path / "filter-ac.net",
    )

    assert prepared.instruction == ".ac list 1k 10k 100k"


def test_prepare_ac_list_sweep_requires_frequencies(tmp_path: Path) -> None:
    netlist = tmp_path / "filter.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    with pytest.raises(ValueError, match="frequencies"):
        prepare_ac(netlist, workspace_root=tmp_path, sweep_type="list")

    with pytest.raises(ValueError, match="requires points, start, and stop"):
        prepare_ac(netlist, workspace_root=tmp_path, sweep_type="dec")
