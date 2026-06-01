"""Focused tests for the starter schematic authoring workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services.schematic.create_starter_schematic import (
    create_starter_schematic,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_create_starter_schematic_builds_source_load_template(tmp_path: Path) -> None:
    result = create_starter_schematic(tmp_path / "starter.qsch", workspace_root=tmp_path)

    reopened, _, _ = open_schematic_editor(result.output_path, workspace_root=tmp_path)
    components = tuple(str(reference) for reference in reopened.get_components())
    net_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "net"]
    wire_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "wire"]

    assert result.source_reference == "V1"
    assert result.load_reference == "R1"
    assert components == ("V1", "R1")
    assert reopened.get_component_value("V1") == "10"
    assert reopened.get_component_value("R1") == "1k"
    assert ["net", "(400,600)", "1", "14", "0", '"VOUT"'] in net_tokens
    assert ["net", "(400,200)", "1", "13", "0", '"GND"'] in net_tokens
    assert ["wire", "(400,600)", "(800,600)", '"VOUT"'] in wire_tokens
    assert ["wire", "(400,200)", "(800,200)", '"GND"'] in wire_tokens
