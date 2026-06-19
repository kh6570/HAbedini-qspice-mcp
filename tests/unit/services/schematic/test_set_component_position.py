"""Tests for set_component_position service and backend."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    add_simple_component,
    component_rotation_index_to_degrees,
    create_blank_schematic_file,
    open_schematic_editor,
)
from qspice_mcp.services._backends.schematic_editor_edits import set_component_position
from qspice_mcp.services.schematic.set_component_position import (
    set_component_position as move_component_service,
)

if TYPE_CHECKING:
    from pathlib import Path

set_component_position_module = importlib.import_module(
    "qspice_mcp.services.schematic.set_component_position"
)


def test_set_component_position_moves_part_without_changing_rotation(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(160, 240),
        rotation_degrees=90,
    )
    editor.save_as(output_path)

    set_component_position(editor, reference="R1", position_x=320, position_y=480)
    editor.save_as(output_path)

    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    position, rotation_index = reopened.get_component_position("R1")
    assert (position.X, position.Y) == (320, 480)
    assert component_rotation_index_to_degrees(rotation_index) == 90


def test_set_component_position_service_persists_edit(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    saved = tmp_path / "demo-moved.qsch"

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None,
        apply_edit,
    ):
        del workspace_root
        apply_edit(object())
        return schematic.resolve(strict=False), saved.resolve(strict=False)

    def fake_apply_component_position(
        editor: object,
        *,
        reference: str,
        position_x: int,
        position_y: int,
        rotation_degrees: int | None = None,
    ) -> tuple[int, int, int]:
        del editor
        assert reference == "R1"
        assert position_x == 100
        assert position_y == 200
        assert rotation_degrees is None
        return 100, 200, 90

    monkeypatch.setattr(set_component_position_module, "edit_schematic", fake_edit_schematic)
    monkeypatch.setattr(
        set_component_position_module,
        "apply_component_position",
        fake_apply_component_position,
    )

    result = move_component_service(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        position_x=100,
        position_y=200,
        output_path=saved,
    )

    assert result.position_x == 100
    assert result.position_y == 200
    assert result.rotation_degrees == 90
