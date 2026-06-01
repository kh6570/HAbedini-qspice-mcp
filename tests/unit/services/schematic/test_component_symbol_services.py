"""Tests for component symbol metadata services."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from qspice_mcp.services._backends.schematic_editor import (
    ComponentSymbolMetadata,
    SymbolDrawingMetadata,
    SymbolPinMetadata,
    SymbolTextMetadata,
)
from qspice_mcp.services.schematic.add_component_symbol_drawing import (
    add_component_symbol_drawing,
)
from qspice_mcp.services.schematic.add_dll_block_pin import add_dll_block_pin
from qspice_mcp.services.schematic.read_component_symbol import read_component_symbol
from qspice_mcp.services.schematic.remove_component_symbol_drawing import (
    remove_component_symbol_drawing,
)
from qspice_mcp.services.schematic.remove_dll_block_pin import remove_dll_block_pin
from qspice_mcp.services.schematic.set_component_symbol_drawing import (
    set_component_symbol_drawing,
)
from qspice_mcp.services.schematic.set_component_symbol_pin import set_component_symbol_pin
from qspice_mcp.services.schematic.set_component_symbol_text import set_component_symbol_text
from qspice_mcp.services.schematic.set_dll_block_pin_role import set_dll_block_pin_role

_add_component_symbol_drawing_service = importlib.import_module(
    "qspice_mcp.services.schematic.add_component_symbol_drawing"
)
_add_dll_block_pin_service = importlib.import_module(
    "qspice_mcp.services.schematic.add_dll_block_pin"
)
_read_component_symbol_service = importlib.import_module(
    "qspice_mcp.services.schematic.read_component_symbol"
)
_remove_dll_block_pin_service = importlib.import_module(
    "qspice_mcp.services.schematic.remove_dll_block_pin"
)
_remove_component_symbol_drawing_service = importlib.import_module(
    "qspice_mcp.services.schematic.remove_component_symbol_drawing"
)
_set_component_symbol_drawing_service = importlib.import_module(
    "qspice_mcp.services.schematic.set_component_symbol_drawing"
)
_set_dll_block_pin_role_service = importlib.import_module(
    "qspice_mcp.services.schematic.set_dll_block_pin_role"
)
_set_component_symbol_text_service = importlib.import_module(
    "qspice_mcp.services.schematic.set_component_symbol_text"
)
_set_component_symbol_pin_service = importlib.import_module(
    "qspice_mcp.services.schematic.set_component_symbol_pin"
)


class FakeEditor:
    pass


def test_read_component_symbol_returns_backend_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    monkeypatch.setattr(
        _read_component_symbol_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _read_component_symbol_service,
        "read_component_symbol_metadata",
        lambda editor, *, reference: _read_component_symbol_service.ComponentSymbolRead(
            schematic_path=schematic.resolve(strict=False),
            reference=reference,
            symbol_name="Comparator",
            type_name="X",
            description="Threshold Comparator",
            library_file=None,
            shorted_pins=False,
            text_attributes=(
                SymbolTextMetadata(0, "reference", "X1", 50, 350, 1, 0, None, False, "0x1000000"),
            ),
            pins=(SymbolPinMetadata(0, "in+", -400, -200, 20, 0, 1, 7, 0, "0x0", -1, None),),
            drawing_items=(
                SymbolDrawingMetadata(
                    0,
                    "triangle",
                    ("(0,80)", "(100,-70)", "(-100,-70)"),
                    ((0, 80), (100, -70), (-100, -70)),
                    (),
                ),
            ),
            drawing_tags=("triangle",),
            image_asset_tokens=(),
        ),
    )

    result = read_component_symbol(schematic, workspace_root=tmp_path, reference="X1")

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.reference == "X1"
    assert result.symbol_name == "Comparator"
    assert result.text_attributes[0].text == "X1"
    assert result.pins[0].name == "in+"
    assert result.drawing_items[0].tag_name == "triangle"


def test_set_component_symbol_text_persists_updated_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _set_component_symbol_text_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_text_service,
        "set_component_symbol_text_attributes",
        lambda editor_obj, **kwargs: SymbolTextMetadata(
            index=1,
            role="value",
            text=str(kwargs["text"]),
            position_x=140,
            position_y=-120,
            size=2,
            rotation_code=45,
            rotation_degrees=90,
            is_comment=True,
            color_code="0x12ab34",
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_text_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = set_component_symbol_text(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        text_role="value",
        text="22k",
        position_x=140,
        position_y=-120,
        size=2,
        rotation_code=45,
        is_comment=True,
        color_code="0x12ab34",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "R1"
    assert result.text_attribute.text == "22k"
    assert result.text_attribute.rotation_degrees == 90


def test_add_component_symbol_drawing_persists_updated_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _add_component_symbol_drawing_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _add_component_symbol_drawing_service,
        "add_component_symbol_drawing_metadata",
        lambda editor_obj, **kwargs: SymbolDrawingMetadata(
            index=int(kwargs["insert_index"]),
            tag_name=str(kwargs["tag_name"]),
            arguments=tuple(str(argument) for argument in kwargs["arguments"]),
            coordinate_points=((-150, 150), (150, -150)),
            image_asset_tokens=(),
        ),
    )
    monkeypatch.setattr(
        _add_component_symbol_drawing_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = add_component_symbol_drawing(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        tag_name="ellipse",
        arguments=[
            "(-150,150)",
            "(150,-150)",
            "0",
            "0",
            "0",
            "0x1000000",
            "0x3000000",
            "-1",
            "-1",
        ],
        insert_index=1,
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "R1"
    assert result.drawing_item.index == 1
    assert result.drawing_item.tag_name == "ellipse"


def test_set_component_symbol_drawing_persists_updated_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _set_component_symbol_drawing_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_drawing_service,
        "set_component_symbol_drawing_metadata",
        lambda editor_obj, **kwargs: SymbolDrawingMetadata(
            index=int(kwargs["drawing_index"]),
            tag_name="zigzag",
            arguments=(
                "(-100,180)",
                "(100,-180)",
                "0",
                "0",
                "0",
                "0x12ab34",
                "-1",
                "-1",
            ),
            coordinate_points=((-100, 180), (100, -180)),
            image_asset_tokens=(),
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_drawing_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = set_component_symbol_drawing(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        drawing_index=2,
        arguments=[
            "(-100,180)",
            "(100,-180)",
            "0",
            "0",
            "0",
            "0x12ab34",
            "-1",
            "-1",
        ],
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "R1"
    assert result.drawing_item.index == 2
    assert result.drawing_item.arguments[-3] == "0x12ab34"


def test_remove_component_symbol_drawing_persists_updated_metadata(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _remove_component_symbol_drawing_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _remove_component_symbol_drawing_service,
        "remove_component_symbol_drawing_metadata",
        lambda editor_obj, **kwargs: SymbolDrawingMetadata(
            index=int(kwargs["drawing_index"]),
            tag_name="ellipse",
            arguments=(
                "(-150,150)",
                "(150,-150)",
                "0",
                "0",
                "0",
                "0x1000000",
                "0x3000000",
                "-1",
                "-1",
            ),
            coordinate_points=((-150, 150), (150, -150)),
            image_asset_tokens=(),
        ),
    )
    monkeypatch.setattr(
        _remove_component_symbol_drawing_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = remove_component_symbol_drawing(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        drawing_index=3,
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "R1"
    assert result.drawing_item.index == 3
    assert result.drawing_item.tag_name == "ellipse"


def test_set_component_symbol_pin_persists_updated_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _set_component_symbol_pin_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_pin_service,
        "set_component_symbol_pin_metadata",
        lambda editor_obj, **kwargs: SymbolPinMetadata(
            index=0,
            name=str(kwargs["new_pin_name"]),
            position_x=0,
            position_y=200,
            label_position_x=20,
            label_position_y=0,
            text_size=1,
            label_anchor_code=7,
            pin_kind_code=3,
            color_code="0x0",
            aux_code=-1,
            behavioral_net_override="VIN_OVERRIDE",
        ),
    )
    monkeypatch.setattr(
        _set_component_symbol_pin_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = set_component_symbol_pin(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        pin_index=0,
        new_pin_name="IN",
        label_position_x=20,
        label_position_y=0,
        label_anchor_code=7,
        pin_kind_code=3,
        behavioral_net_override="VIN_OVERRIDE",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "R1"
    assert result.pin.name == "IN"
    assert result.pin.behavioral_net_override == "VIN_OVERRIDE"


def test_add_dll_block_pin_persists_updated_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _add_dll_block_pin_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _add_dll_block_pin_service,
        "add_dll_block_pin_metadata",
        lambda editor_obj, **kwargs: (
            SymbolPinMetadata(
                1, str(kwargs["pin_name"]), -800, -200, 150, -50, 0, 14, 145, "0x0", -1
            ),
            ComponentSymbolMetadata(
                symbol_name="",
                type_name="Ø(.DLL)",
                description=None,
                library_file=None,
                shorted_pins=False,
                text_attributes=(),
                pins=(
                    SymbolPinMetadata(0, "in0", -800, 0, 150, -50, 0, 14, 145, "0x0", -1),
                    SymbolPinMetadata(
                        1, str(kwargs["pin_name"]), -800, -200, 150, -50, 0, 14, 145, "0x0", -1
                    ),
                    SymbolPinMetadata(2, "out0", 600, 0, -150, -50, 0, 14, 146, "0x0", -1),
                ),
                drawing_items=(),
                drawing_tags=(),
                image_asset_tokens=(),
            ),
        ),
    )
    monkeypatch.setattr(
        _add_dll_block_pin_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = add_dll_block_pin(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        pin_name="clk",
        direction="input",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "X1"
    assert result.pin.name == "clk"
    assert result.input_pin_names == ("in0", "clk")
    assert result.output_pin_names == ("out0",)


def test_remove_dll_block_pin_persists_updated_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _remove_dll_block_pin_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _remove_dll_block_pin_service,
        "remove_dll_block_pin_metadata",
        lambda editor_obj, **kwargs: (
            SymbolPinMetadata(1, "clk", -800, -200, 150, -50, 0, 14, 145, "0x0", -1),
            ComponentSymbolMetadata(
                symbol_name="",
                type_name="Ø(.DLL)",
                description=None,
                library_file=None,
                shorted_pins=False,
                text_attributes=(),
                pins=(
                    SymbolPinMetadata(0, "in0", -800, 0, 150, -50, 0, 14, 145, "0x0", -1),
                    SymbolPinMetadata(1, "out0", 600, 0, -150, -50, 0, 14, 146, "0x0", -1),
                ),
                drawing_items=(),
                drawing_tags=(),
                image_asset_tokens=(),
            ),
        ),
    )
    monkeypatch.setattr(
        _remove_dll_block_pin_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = remove_dll_block_pin(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        pin_name="clk",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "X1"
    assert result.removed_pin_name == "clk"
    assert result.input_pin_names == ("in0",)
    assert result.output_pin_names == ("out0",)


def test_set_dll_block_pin_role_persists_updated_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()

    monkeypatch.setattr(
        _set_dll_block_pin_role_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _set_dll_block_pin_role_service,
        "set_dll_block_pin_role_metadata",
        lambda editor_obj, **kwargs: (
            SymbolPinMetadata(1, "in0", 600, -200, -150, -50, 0, 14, 146, "0x0", -1),
            ComponentSymbolMetadata(
                symbol_name="",
                type_name="Ø(.DLL)",
                description=None,
                library_file=None,
                shorted_pins=False,
                text_attributes=(),
                pins=(
                    SymbolPinMetadata(0, "out0", 600, 0, -150, -50, 0, 14, 146, "0x0", -1),
                    SymbolPinMetadata(1, "in0", 600, -200, -150, -50, 0, 14, 146, "0x0", -1),
                ),
                drawing_items=(),
                drawing_tags=(),
                image_asset_tokens=(),
            ),
        ),
    )
    monkeypatch.setattr(
        _set_dll_block_pin_role_service,
        "save_edited_schematic",
        lambda editor_obj, *, schematic_path, workspace_root, output_path: Path(
            output_path
        ).resolve(strict=False),
    )

    result = set_dll_block_pin_role(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        pin_name="in0",
        pin_role="output",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "X1"
    assert result.pin.name == "in0"
    assert result.pin.position_x == 600
    assert result.input_pin_names == ()
    assert result.output_pin_names == ("out0", "in0")


def test_set_component_symbol_text_requires_complete_position_pair(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    with pytest.raises(ValueError, match="position_x and position_y"):
        set_component_symbol_text(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            text_role="value",
            position_x=10,
        )


def test_set_component_symbol_pin_requires_complete_label_position_pair(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    with pytest.raises(ValueError, match="label_position_x and label_position_y"):
        set_component_symbol_pin(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            pin_index=0,
            label_position_x=20,
        )
