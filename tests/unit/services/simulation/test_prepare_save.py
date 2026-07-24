"""Tests for the `.save` preparation service."""

from __future__ import annotations

import pytest

from qspice_mcp.services.simulation.prepare_save import prepare_save


def test_prepare_save_appends_to_netlist_copy(tmp_path) -> None:
    netlist = tmp_path / "smps.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")
    staged = tmp_path / "smps-save.net"

    prepared = prepare_save(
        netlist,
        workspace_root=tmp_path,
        patterns=["V(out)", "I?(M1)"],
        output_path=staged,
    )

    assert prepared.source_kind == "netlist"
    assert prepared.instruction == ".save V(out) I?(M1)"
    assert staged.read_text(encoding="utf-8") == "* base\n.save V(out) I?(M1)\n.end\n"
    assert any(".noise" in warning for warning in prepared.warnings)


def test_prepare_save_rejects_empty_patterns(tmp_path) -> None:
    netlist = tmp_path / "smps.net"
    netlist.write_text("* base\n.end\n", encoding="utf-8")

    with pytest.raises(ValueError, match="at least one"):
        prepare_save(netlist, workspace_root=tmp_path, patterns=["", "  "])
