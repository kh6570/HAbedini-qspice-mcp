"""Tests for add_junction service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services.schematic.add_junction import add_junction
from qspice_mcp.services.schematic.create_schematic import create_schematic

if TYPE_CHECKING:
    from pathlib import Path


def test_add_junction_persists_junction_tag(tmp_path: Path) -> None:
    created = create_schematic(tmp_path / "blank.qsch", workspace_root=tmp_path)
    result = add_junction(
        created.output_path,
        workspace_root=tmp_path,
        position_x=2500,
        position_y=2700,
    )

    editor, _, _ = open_schematic_editor(result.output_path, workspace_root=tmp_path)
    junction_tags = [item for item in editor.schematic.items if item.tag == "junction"]
    assert len(junction_tags) == 1
    assert junction_tags[0].tokens[1] == "(2500,2700)"
