"""Tests for the `.dc` preparation service."""

from __future__ import annotations

import importlib
from pathlib import Path

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
