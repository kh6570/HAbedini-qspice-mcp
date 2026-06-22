"""Tests for analysis directive placement."""

from __future__ import annotations

from pathlib import Path

import pytest

from qspice_mcp.services._backends.directive_placement import compute_directive_position
from qspice_mcp.services._backends.schematic_editor import (
    add_simple_component,
    create_blank_schematic_file,
    open_schematic_editor,
)
from qspice_mcp.services.schematic.add_instruction import add_instruction


def test_compute_directive_position_below_components() -> None:
    x, y = compute_directive_position(((100, 800), (700, 1000)), 0)
    assert x == 100
    assert y == 1360


def test_compute_directive_position_empty_schematic_fallback() -> None:
    x, y = compute_directive_position((), 0)
    assert x == 100
    assert y == -40


def test_add_instruction_places_below_components(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "layout.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="voltage_source",
        reference="V1",
        value="PULSE(0 5 0 1n 1n 5u 10u)",
        position=(100, 800),
        rotation_degrees=0,
    )
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(700, 1000),
        rotation_degrees=0,
    )
    editor.add_instruction(".tran 100n 50u")
    editor.save_as(output_path)

    text = output_path.read_text(encoding="latin-1")
    assert "text (100,1360) 1 0 0 0x1000000 -1 -1 \".tran 100n 50u\"" in text


def test_add_instruction_service_places_below_components(tmp_path: Path) -> None:
    source, _ = create_blank_schematic_file(tmp_path / "layout.qsch", workspace_root=tmp_path)
    destination = tmp_path / "layout-tran.qsch"
    editor, _, _ = open_schematic_editor(source, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(400, 600),
        rotation_degrees=0,
    )
    editor.save_as(source)

    add_instruction(
        source,
        workspace_root=tmp_path,
        instruction=".tran 100n 50u",
        output_path=destination,
    )

    text = destination.read_text(encoding="latin-1")
    assert "text (400,960) 1 0 0 0x1000000 -1 -1" in text


def test_compute_directive_position_rejects_negative_index() -> None:
    with pytest.raises(ValueError, match="directive_index"):
        compute_directive_position((), -1)
