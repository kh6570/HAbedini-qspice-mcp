"""Tests for the `.tran` preparation service."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.simulation.prepare_transient import prepare_transient

prepare_transient_module = importlib.import_module(
    "qspice_mcp.services.simulation.prepare_transient"
)


def test_prepare_transient_stages_schematic(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "buck.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    staged = tmp_path / "buck-tran.qsch"

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert Path(schematic_path) == schematic.resolve(strict=False)
        assert instruction == ".tran 1u 10m UIC SKIPBP"
        assert Path(output_path or staged) == staged
        staged.write_text("schematic", encoding="utf-8")
        return InstructionAdd(
            schematic_path=schematic.resolve(strict=False),
            output_path=staged.resolve(strict=False),
            instruction=instruction,
        )

    monkeypatch.setattr(prepare_transient_module, "add_instruction_service", fake_add_instruction)

    prepared = prepare_transient(
        schematic,
        workspace_root=tmp_path,
        step="1u",
        stop="10m",
        use_initial_conditions=True,
        skip_bias_point=True,
        output_path=staged,
    )

    assert prepared.source_kind == "schematic"
    assert prepared.output_path == staged.resolve(strict=False)
    assert prepared.instruction.endswith("SKIPBP")


def test_prepare_transient_appends_to_netlist_copy(tmp_path: Path) -> None:
    netlist = tmp_path / "buck.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "artifacts" / "buck-tran.net"

    prepared = prepare_transient(
        netlist,
        workspace_root=tmp_path,
        step="1u",
        stop="10m",
        max_step="100n",
        output_path=staged,
    )

    assert prepared.source_kind == "netlist"
    assert prepared.output_path == staged.resolve(strict=False)
    assert staged.read_text(encoding="utf-8") == "* base\n.tran 1u 10m 0 100n\n.end\n"
