"""Tests for analysis directive preparation services."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_noise import prepare_noise
from qspice_mcp.services.simulation.prepare_sensitivity import prepare_sensitivity
from qspice_mcp.services.simulation.prepare_temperature_sweep import prepare_temperature_sweep
from qspice_mcp.services.simulation.prepare_transfer_function import prepare_transfer_function

analysis_directive_module = importlib.import_module(
    "qspice_mcp.services.simulation._analysis_directive"
)


def test_prepare_noise_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "amp.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "amp-noise.qsch"

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert instruction == ".noise V(out) VIN dec 100 1 1Meg"
        assert Path(output_path or staged) == staged
        staged.write_text("schematic", encoding="utf-8")
        return InstructionAdd(
            schematic_path=schematic.resolve(strict=False),
            output_path=staged.resolve(strict=False),
            instruction=instruction,
        )

    monkeypatch.setattr(analysis_directive_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_noise(
        schematic,
        workspace_root=tmp_path,
        output_node="V(out)",
        input_source="VIN",
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.instruction == ".noise V(out) VIN dec 100 1 1Meg"


def test_prepare_noise_appends_to_netlist(tmp_path) -> None:
    netlist = tmp_path / "amp.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "amp-noise.net"

    prepared = prepare_noise(
        netlist,
        workspace_root=tmp_path,
        output_node="V(out)",
        input_source="VIN",
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
        output_path=staged,
    )

    assert prepared.instruction == ".noise V(out) VIN dec 100 1 1Meg"
    assert staged.read_text(encoding="utf-8") == "* base\n.noise V(out) VIN dec 100 1 1Meg\n.end\n"


def test_prepare_transfer_function_appends_to_netlist(tmp_path) -> None:
    netlist = tmp_path / "amp.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "amp-tf.net"

    prepared = prepare_transfer_function(
        netlist,
        workspace_root=tmp_path,
        output_node="V(out)",
        input_source="VIN",
        output_path=staged,
    )

    assert prepared.instruction == ".tf V(out) VIN"
    assert staged.read_text(encoding="utf-8") == "* base\n.tf V(out) VIN\n.end\n"


def test_prepare_sensitivity_appends_to_netlist(tmp_path) -> None:
    netlist = tmp_path / "amp.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "amp-sens.net"

    prepared = prepare_sensitivity(
        netlist,
        workspace_root=tmp_path,
        analysis_type="dc",
        output_node="V(out)",
        output_path=staged,
    )

    assert prepared.instruction == ".sens dc V(out)"


def test_prepare_temperature_sweep_appends_to_netlist(tmp_path) -> None:
    netlist = tmp_path / "amp.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "amp-temp.net"

    prepared = prepare_temperature_sweep(
        netlist,
        workspace_root=tmp_path,
        start="-40",
        stop="125",
        step="25",
        output_path=staged,
    )

    assert prepared.instruction == ".step temp -40 125 25"
