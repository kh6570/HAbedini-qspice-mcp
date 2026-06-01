"""Tests for the `.bode` preparation service."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_bode_analysis import prepare_bode_analysis

prepare_bode_module = importlib.import_module(
    "qspice_mcp.services.simulation.prepare_bode_analysis"
)


def test_prepare_bode_analysis_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "loop.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "loop-bode.qsch"

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert Path(schematic_path) == schematic.resolve(strict=False)
        assert instruction == ".bode VPERT 5m 1k 1Meg 2m SQUARE=10 DEBUG SKIPBP UIC"
        assert Path(output_path or staged) == staged
        staged.write_text("schematic", encoding="utf-8")
        return InstructionAdd(
            schematic_path=schematic.resolve(strict=False),
            output_path=staged.resolve(strict=False),
            instruction=instruction,
        )

    monkeypatch.setattr(prepare_bode_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_bode_analysis(
        schematic,
        workspace_root=tmp_path,
        perturbation_source="VPERT",
        settling_time="5m",
        start_frequency="1k",
        stop_frequency="1Meg",
        injection_amplitude="2m",
        square_periods=10,
        debug=True,
        skip_bias_point=True,
        use_initial_conditions=True,
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.output_path == staged.resolve(strict=False)
    assert prepared.instruction.endswith("UIC")


def test_prepare_bode_analysis_appends_to_netlist_copy(tmp_path: Path) -> None:
    netlist = tmp_path / "loop.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "artifacts" / "loop-bode.net"

    prepared = prepare_bode_analysis(
        netlist,
        workspace_root=tmp_path,
        perturbation_source="VPERT",
        settling_time="5m",
        start_frequency="1k",
        stop_frequency="1Meg",
        injection_amplitude="2m",
        output_path=staged,
    )

    assert prepared.source_kind == "netlist"
    assert prepared.output_path == staged.resolve(strict=False)
    assert staged.read_text(encoding="utf-8") == "* base\n.bode VPERT 5m 1k 1Meg 2m\n.end\n"
