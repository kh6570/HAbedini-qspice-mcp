"""Tests for loop-gain analysis preparation."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_loop_gain_analysis import prepare_loop_gain_analysis

prepare_loop_gain_module = importlib.import_module(
    "qspice_mcp.services.simulation.prepare_loop_gain_analysis"
)


def test_prepare_loop_gain_analysis_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "regulator.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "regulator-loop-gain-tian.qsch"

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

    monkeypatch.setattr(prepare_loop_gain_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_loop_gain_analysis(
        schematic,
        workspace_root=tmp_path,
        method="tian",
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.method == "tian"
    assert prepared.reference_example == "Tian.qsch"
    assert prepared.expected_loop_gain_signal == "OpenLoopGain"


def test_prepare_loop_gain_analysis_appends_netlist_comments(tmp_path: Path) -> None:
    netlist = tmp_path / "regulator.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "artifacts" / "regulator-loop-gain-middlebrook.net"

    prepared = prepare_loop_gain_analysis(
        netlist,
        workspace_root=tmp_path,
        method="middlebrook",
        sweep_type="oct",
        points="20",
        start="10",
        stop="100k",
        expected_loop_gain_signal="LoopGain",
        output_path=staged,
    )

    rendered = staged.read_text(encoding="utf-8")
    assert prepared.source_kind == "netlist"
    assert prepared.expected_loop_gain_signal == "LoopGain"
    assert "* loop gain analysis: middlebrook method" in rendered
    assert ".ac oct 20 10 100k" in rendered
    assert rendered.endswith(".end\n")
