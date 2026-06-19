"""Tests for schematic backend helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import QSpiceError

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.subcircuit_fixtures import (
    supported_leaf_subcircuit_definition_bytes,
    supported_subcircuit_schematic_bytes,
)

from qspice_mcp.services._backends._qsch_support import QschTag
from qspice_mcp.services._backends.schematic_editor import (
    add_component_symbol_drawing_metadata,
    add_dll_block,
    add_dll_block_pin_metadata,
    add_junction,
    add_net_label,
    add_simple_component,
    add_wire,
    component_rotation_index_to_degrees,
    create_blank_schematic_file,
    open_schematic_editor,
    read_component_symbol_metadata,
    remove_component_symbol_drawing_metadata,
    remove_dll_block_pin_metadata,
    remove_junction,
    remove_net_label,
    remove_wire,
    resolve_component_pin_position,
    set_component_rotation,
    set_component_symbol_drawing_metadata,
    set_component_symbol_pin_metadata,
    set_component_symbol_text_attributes,
    set_dll_block_pin_role_metadata,
)


def test_create_blank_schematic_file_writes_minimal_qsch(tmp_path: Path) -> None:
    output_path, overwritten = create_blank_schematic_file(
        tmp_path / "blank.qsch",
        workspace_root=tmp_path,
    )

    reopened, resolved_path, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    assert overwritten is False
    assert resolved_path == output_path
    assert tuple(str(reference) for reference in reopened.get_components()) == ()


def test_component_rotation_index_round_trip() -> None:
    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        index = degrees // 45
        assert component_rotation_index_to_degrees(index) == degrees


def test_set_component_rotation_updates_index_without_moving_part(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(160, 240),
        rotation_degrees=0,
    )
    set_component_rotation(editor, reference="R1", rotation_degrees=90)
    editor.save_as(output_path)

    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    position, rotation_index = reopened.get_component_position("R1")
    assert (position.X, position.Y) == (160, 240)
    assert rotation_index == 2
    assert component_rotation_index_to_degrees(rotation_index) == 90


def test_add_instruction_writes_micro_sign_without_utf8_bom(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    editor.add_instruction(".tran 0 300\u00b5 0 100n uic")
    editor.save_as(output_path)

    raw_bytes = output_path.read_bytes()
    assert b"\xef\xbb\xbf.tran" not in raw_bytes
    assert b".tran 0 300\xb5 0 100n uic" in raw_bytes


def test_add_simple_component_adds_resistor_to_blank_schematic(tmp_path: Path) -> None:
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
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    position, rotation = reopened.get_component_position("R1")
    assert tuple(str(reference) for reference in reopened.get_components()) == ("R1",)
    assert reopened.get_component_value("R1") == "10k"
    assert (position.X, position.Y) == (160, 240)
    assert rotation == 2


def test_add_simple_component_supports_more_simple_kinds(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="voltage_source",
        reference="V1",
        value="12",
        position=(0, 0),
    )
    add_simple_component(
        editor,
        component_kind="capacitor",
        reference="C1",
        value="10u",
        position=(400, 0),
    )
    add_simple_component(
        editor,
        component_kind="diode",
        reference="D1",
        value="1N4148",
        position=(800, 0),
    )
    add_simple_component(
        editor,
        component_kind="ground",
        reference=None,
        value=None,
        position=(0, 400),
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    components = tuple(str(reference) for reference in reopened.get_components())
    net_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "net"]

    assert components == ("V1", "C1", "D1")
    assert reopened.get_component_value("V1") == "12"
    assert reopened.get_component_value("C1") == "10u"
    assert reopened.get_component_value("D1") == "1N4148"
    assert ["net", "(0,400)", "1", "13", "0", '"GND"'] in net_tokens


def test_add_simple_component_supports_power_stage_kinds(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="inductor",
        reference="L1",
        value="50u",
        position=(0, 0),
    )
    add_simple_component(
        editor,
        component_kind="nmos",
        reference="M1",
        value="BSC123N08NS3",
        position=(400, 0),
    )
    add_simple_component(
        editor,
        component_kind="pmos",
        reference="M2",
        value="PMOS",
        position=(800, 0),
    )
    add_simple_component(
        editor,
        component_kind="behavioral",
        reference="B1",
        value="V=V(PWM)",
        position=(1200, 0),
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    components = tuple(str(reference) for reference in reopened.get_components())
    assert components == ("L1", "M1", "M2", "B1")
    assert reopened.get_component_value("L1") == "50u"
    saved_text = output_path.read_bytes().decode("latin-1")
    assert "library file: NMOS.txt" in saved_text
    assert "library file: PMOS.txt" in saved_text


def test_add_dll_block_adds_custom_device_to_blank_schematic(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    input_pins, output_pins = add_dll_block(
        editor,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=("in0", "clk"),
        output_pin_names=("pwm", "saw"),
        position=(300, 100),
        rotation_degrees=0,
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    position, rotation = reopened.get_component_position("X1")
    metadata = read_component_symbol_metadata(reopened, reference="X1")

    assert input_pins == ("in0", "clk")
    assert output_pins == ("pwm", "saw")
    assert tuple(str(reference) for reference in reopened.get_components()) == ("X1",)
    assert (position.X, position.Y) == (300, 100)
    assert rotation == 0
    assert metadata.type_name == "Ø(.DLL)"
    assert tuple(text.text for text in metadata.text_attributes[:2]) == ("X1", "Buck_controller")
    assert tuple(pin.name for pin in metadata.pins) == ("in0", "clk", "pwm", "saw")


def test_set_component_symbol_pin_metadata_updates_created_dll_block(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_dll_block(
        editor,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=("in0",),
        output_pin_names=("out0",),
        position=(0, 0),
        rotation_degrees=0,
    )
    metadata = set_component_symbol_pin_metadata(
        editor,
        reference="X1",
        pin_index=0,
        new_pin_name="VIN",
        pin_kind_code=150,
        label_anchor_code=15,
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    updated = read_component_symbol_metadata(reopened, reference="X1")

    assert metadata.name == "VIN"
    assert metadata.pin_kind_code == 150
    assert metadata.label_anchor_code == 15
    assert tuple(pin.name for pin in updated.pins) == ("VIN", "out0")


def test_add_dll_block_pin_metadata_updates_created_dll_block(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_dll_block(
        editor,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=("in0",),
        output_pin_names=("out0",),
        position=(0, 0),
        rotation_degrees=0,
    )
    pin, metadata = add_dll_block_pin_metadata(
        editor,
        reference="X1",
        pin_name="clk",
        direction="input",
        insert_index=1,
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    updated = read_component_symbol_metadata(reopened, reference="X1")

    assert pin.name == "clk"
    assert tuple(component_pin.name for component_pin in metadata.pins) == ("in0", "clk", "out0")
    assert tuple(component_pin.name for component_pin in updated.pins) == ("in0", "clk", "out0")
    assert updated.pins[1].position_x == -800


def test_remove_dll_block_pin_metadata_updates_created_dll_block(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_dll_block(
        editor,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=("in0", "clk"),
        output_pin_names=("out0",),
        position=(0, 0),
        rotation_degrees=0,
    )
    removed_pin, metadata = remove_dll_block_pin_metadata(
        editor,
        reference="X1",
        pin_name="clk",
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    updated = read_component_symbol_metadata(reopened, reference="X1")

    assert removed_pin.name == "clk"
    assert tuple(component_pin.name for component_pin in metadata.pins) == ("in0", "out0")
    assert tuple(component_pin.name for component_pin in updated.pins) == ("in0", "out0")


def test_set_dll_block_pin_role_metadata_moves_pin_between_groups(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_dll_block(
        editor,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=("in0",),
        output_pin_names=("out0",),
        position=(0, 0),
        rotation_degrees=0,
    )
    pin, metadata = set_dll_block_pin_role_metadata(
        editor,
        reference="X1",
        pin_name="in0",
        pin_role="output",
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    updated = read_component_symbol_metadata(reopened, reference="X1")

    assert pin.name == "in0"
    assert pin.position_x == 600
    assert tuple(component_pin.name for component_pin in metadata.pins) == ("out0", "in0")
    assert tuple(component_pin.name for component_pin in updated.pins) == ("out0", "in0")


def test_add_wire_and_net_label_persist_to_blank_schematic(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_net_label(editor, net_name="VIN", position=(0, 0))
    add_wire(editor, start=(0, 0), end=(400, 0), net_name="VIN")
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    net_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "net"]
    wire_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "wire"]

    assert ["net", "(0,0)", "1", "14", "0", '"VIN"'] in net_tokens
    assert ["wire", "(0,0)", "(400,0)", '"VIN"'] in wire_tokens


def test_remove_wire_persists_to_blank_schematic(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_wire(editor, start=(0, 0), end=(400, 0), net_name="VIN")
    remove_wire(editor, start=(0, 0), end=(400, 0), net_name="VIN")
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    wire_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "wire"]
    assert wire_tokens == []


def test_remove_net_label_and_junction_persist_to_blank_schematic(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_net_label(editor, net_name="VIN", position=(0, 0))
    add_junction(editor, position=(200, 0))
    remove_net_label(editor, position=(0, 0), net_name="VIN")
    remove_junction(editor, position=(200, 0))
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    net_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "net"]
    junction_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "junction"]
    assert net_tokens == []
    assert junction_tokens == []


def test_add_wire_can_snap_to_component_pins(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="voltage_source",
        reference="V1",
        value="10",
        position=(0, 0),
    )
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(400, 0),
    )

    assert resolve_component_pin_position(editor, reference="V1", pin_name="+") == (0, 200)
    assert resolve_component_pin_position(editor, reference="R1", pin_name="1") == (400, 200)

    add_wire(
        editor,
        start_reference="V1",
        start_pin="+",
        end_reference="R1",
        end_pin="1",
        net_name="VOUT",
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    wire_tokens = [item.tokens for item in reopened.schematic.items if item.tag == "wire"]

    assert ["wire", "(0,200)", "(400,200)", '"VOUT"'] in wire_tokens


def test_read_component_symbol_metadata_reports_embedded_symbol_details(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(160, 240),
        rotation_degrees=0,
    )

    metadata = read_component_symbol_metadata(editor, reference="R1")

    assert metadata.symbol_name == "R"
    assert metadata.type_name == "R"
    assert metadata.description == "Resistor(USA Style Symbol)"
    assert metadata.shorted_pins is False
    assert metadata.drawing_tags == ("line", "zigzag")
    assert tuple(item.tag_name for item in metadata.drawing_items) == ("line", "line", "zigzag")
    assert metadata.drawing_items[0].coordinate_points == ((0, 200), (0, 180))
    assert metadata.drawing_items[2].arguments[-3] == "0x1000000"
    assert metadata.image_asset_tokens == ()
    assert metadata.text_attributes[0].role == "reference"
    assert metadata.text_attributes[0].text == "R1"
    assert metadata.text_attributes[0].position_x == 100
    assert metadata.text_attributes[0].position_y == 150
    assert metadata.text_attributes[1].role == "value"
    assert metadata.text_attributes[1].text == "10k"
    assert metadata.text_attributes[1].rotation_code == 7
    assert metadata.pins[0].name == "1"
    assert metadata.pins[0].position_x == 0
    assert metadata.pins[0].position_y == 200
    assert metadata.pins[0].label_anchor_code == 0
    assert metadata.pins[1].name == "2"


def test_read_component_symbol_metadata_handles_multi_text_multi_pin_symbols(
    tmp_path: Path,
) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="COMPARATOR",
        position=(0, 0),
        rotation_degrees=0,
    )

    component = editor.get_component("R1")
    symbol_tag = component.attributes["tag"].get_items("symbol")[0]
    symbol_tag.tokens[1] = "Comparator"
    symbol_tag.get_items("type:")[0].tokens[1] = "X"
    symbol_tag.get_items("description:")[0].tokens[1] = "Threshold Comparator"
    symbol_tag.items.insert(
        8,
        QschTag("text", "(400,-550)", 1, 0, 0, "0x0", -1, -1, '"Vhigh=1"'),
    )
    symbol_tag.items.insert(
        9,
        QschTag("text", "(400,-700)", 1, 0, 0, "0x0", -1, -1, '"Vlow=0"'),
    )
    symbol_tag.items[-2] = QschTag("pin", "(-400,-200)", "(20,0)", 1, 7, 0, "0x0", -1, '"in+"')
    symbol_tag.items[-1] = QschTag("pin", "(-400,200)", "(230,10)", 1, 11, 0, "0x0", -1, '"in-"')
    symbol_tag.items.append(QschTag("pin", "(400,0)", "(-80,130)", 1, 15, 0, "0x0", -1, '"out"'))

    metadata = read_component_symbol_metadata(editor, reference="R1")

    assert metadata.symbol_name == "Comparator"
    assert metadata.type_name == "X"
    assert metadata.description == "Threshold Comparator"
    assert tuple(text.role for text in metadata.text_attributes) == (
        "reference",
        "value",
        "custom",
        "custom",
    )
    assert metadata.text_attributes[2].text == "Vhigh=1"
    assert metadata.text_attributes[3].text == "Vlow=0"
    assert tuple(item.tag_name for item in metadata.drawing_items) == ("line", "line", "zigzag")
    assert tuple(pin.name for pin in metadata.pins) == ("in+", "in-", "out")
    assert tuple(pin.label_anchor_code for pin in metadata.pins) == (7, 11, 15)


def test_set_component_symbol_drawing_metadata_updates_existing_item(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(0, 0),
        rotation_degrees=0,
    )

    metadata = set_component_symbol_drawing_metadata(
        editor,
        reference="R1",
        drawing_index=2,
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
    )

    assert metadata.tag_name == "zigzag"
    assert metadata.coordinate_points == ((-100, 180), (100, -180))
    assert metadata.arguments[-3] == "0x12ab34"


def test_add_and_remove_component_symbol_drawing_metadata_round_trip(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(0, 0),
        rotation_degrees=0,
    )

    added = add_component_symbol_drawing_metadata(
        editor,
        reference="R1",
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
    )

    assert added.index == 3
    assert added.tag_name == "ellipse"

    removed = remove_component_symbol_drawing_metadata(
        editor,
        reference="R1",
        drawing_index=3,
    )
    remaining = read_component_symbol_metadata(editor, reference="R1")

    assert removed.tag_name == "ellipse"
    assert tuple(item.tag_name for item in remaining.drawing_items) == (
        "line",
        "line",
        "zigzag",
    )


def test_set_component_symbol_text_attributes_updates_value_text_and_layout(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(0, 0),
        rotation_degrees=0,
    )

    metadata = set_component_symbol_text_attributes(
        editor,
        reference="R1",
        text_role="value",
        text="22k",
        position=(140, -120),
        size=2,
        rotation_code=45,
        is_comment=True,
        color_code="0x12ab34",
    )

    assert editor.get_component_value("R1") == "22k"
    assert metadata.role == "value"
    assert metadata.text == "22k"
    assert metadata.position_x == 140
    assert metadata.position_y == -120
    assert metadata.size == 2
    assert metadata.rotation_code == 45
    assert metadata.rotation_degrees == 90
    assert metadata.is_comment is True
    assert metadata.color_code == "0x12ab34"


def test_set_component_symbol_pin_metadata_updates_name_selector_and_behavioral_override(
    tmp_path: Path,
) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(0, 0),
        rotation_degrees=0,
    )

    metadata = set_component_symbol_pin_metadata(
        editor,
        reference="R1",
        pin_index=0,
        new_pin_name="IN",
        label_position=(20, 0),
        label_anchor_code=7,
        pin_kind_code=3,
        behavioral_net_override="VIN_OVERRIDE",
    )

    assert metadata.name == "IN"
    assert metadata.label_position_x == 20
    assert metadata.label_position_y == 0
    assert metadata.label_anchor_code == 7
    assert metadata.pin_kind_code == 3
    assert metadata.behavioral_net_override == "VIN_OVERRIDE"
    assert resolve_component_pin_position(editor, reference="R1", pin_name="IN") == (0, 200)


def test_get_subcircuit_resolves_external_definition_qsch(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(supported_leaf_subcircuit_definition_bytes())

    editor, _, _ = open_schematic_editor(schematic, workspace_root=tmp_path)
    subeditor = editor.get_subcircuit("X1")

    assert tuple(str(reference) for reference in subeditor.get_components()) == ("R1", "C1")
    assert subeditor.get_component_value("R1") == "2k"


def test_get_subcircuit_rejects_non_subcircuit_reference(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "blank.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position=(0, 0),
    )
    editor.save_as(output_path)
    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)

    with pytest.raises(QSpiceError, match="not a subcircuit instance"):
        reopened.get_subcircuit("R1")
