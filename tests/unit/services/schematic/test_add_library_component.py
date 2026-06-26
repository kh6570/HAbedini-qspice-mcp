"""Tests for the add_library_component service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.add_library_component import add_library_component
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.list_components import list_components

if TYPE_CHECKING:
    from pathlib import Path


def test_add_library_component_clones_template_part(tmp_path: Path) -> None:
    template = tmp_path / "template.qsch"
    create_starter_schematic(template, workspace_root=tmp_path)
    target = tmp_path / "target.qsch"
    create_schematic(target, workspace_root=tmp_path)

    result = add_library_component(
        target,
        workspace_root=tmp_path,
        template_path=template,
        template_reference="R1",
        reference="R5",
        position_x=800,
        position_y=400,
        value="4k7",
    )

    assert result.reference == "R5"
    assert result.pin_names == ("1", "2")
    assert result.value == "4k7"

    catalog = list_components(target, workspace_root=tmp_path)
    references = {component.reference for component in catalog.components}
    assert "R5" in references
