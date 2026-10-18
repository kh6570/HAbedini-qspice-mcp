# In the name of God, the Most Gracious, the Most Merciful
"""Regression tests for explicit wire names surviving label replacements."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._backends.schematic_editor import (
    add_net_label as add_label_tag,
)
from qspice_mcp.services._backends.schematic_editor import (
    add_simple_component,
    add_wire,
    create_blank_schematic_file,
    open_schematic_editor,
    resolve_component_pin_position,
)
from qspice_mcp.services.schematic.add_net_label import add_net_label
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic
from qspice_mcp.services.schematic.remove_net_label import remove_net_label
from qspice_mcp.services.schematic.rename_net import rename_net

if TYPE_CHECKING:
    from pathlib import Path


def _input_circuit(tmp_path: Path) -> Path:
    """Create two disconnected input pins joined by labels and one named wire."""

    schematic, _ = create_blank_schematic_file(tmp_path / "input.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(schematic, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="voltage_source",
        reference="V1",
        value="48",
        position=(1000, -1400),
    )
    add_simple_component(
        editor,
        component_kind="inductor",
        reference="L1",
        value="100u",
        position=(900, 200),
        rotation_degrees=90,
    )
    source_pin = resolve_component_pin_position(editor, reference="V1", pin_name="+")
    inductor_pin = resolve_component_pin_position(editor, reference="L1", pin_name="1")
    add_wire(editor, start=(0, 200), end=inductor_pin, net_name="in")
    add_label_tag(editor, position=(0, 200), net_name="in")
    add_label_tag(editor, position=source_pin, net_name="in")
    editor.add_instruction(".meas tran input_voltage FIND V(in) AT=1m")
    editor.save_as(schematic)
    return schematic


def test_rename_net_updates_both_labels_and_wire_without_splitting_input(tmp_path: Path) -> None:
    schematic = _input_circuit(tmp_path)
    source_bytes = schematic.read_bytes()
    output = tmp_path / "renamed.qsch"

    result = rename_net(
        schematic,
        workspace_root=tmp_path,
        net_name="IN",
        new_net_name="vbus",
        output_path=output,
    )

    assert result.labels_renamed == 2
    assert result.wires_renamed == 1
    assert schematic.read_bytes() == source_bytes
    inspection = inspect_schematic(output, workspace_root=tmp_path, include_connectivity=True)
    assert inspection.connectivity is not None
    inputs = next(net for net in inspection.connectivity.nets if net.net == "vbus")
    assert {(pin.reference, pin.pin) for pin in inputs.pins} == {("V1", "+"), ("L1", "1")}
    assert "in" not in {net.net for net in inspection.connectivity.nets}
    original, _, _ = open_schematic_editor(schematic, workspace_root=tmp_path)
    renamed, _, _ = open_schematic_editor(output, workspace_root=tmp_path)
    assert original.schematic is not None
    assert renamed.schematic is not None
    for before, after in zip(original.schematic.items, renamed.schematic.items, strict=True):
        name_index = {"net": 5, "wire": 3}.get(before.tag)
        if name_index is not None:
            assert before.tokens[:name_index] == after.tokens[:name_index]
            assert after.tokens[name_index] == '"vbus"'
        else:
            assert before.out() == after.out()


@pytest.mark.parametrize("position", [(0, 200), (350, 200), (700, 200)])
def test_label_replacement_rejects_stale_wire_without_saving(
    tmp_path: Path, position: tuple[int, int]
) -> None:
    schematic = _input_circuit(tmp_path)
    remove_net_label(
        schematic,
        workspace_root=tmp_path,
        position_x=0,
        position_y=200,
        net_name="in",
    )
    before = schematic.read_bytes()

    with pytest.raises(ValidationError, match=r"explicit wire name.*rename_net"):
        add_net_label(
            schematic,
            workspace_root=tmp_path,
            position_x=position[0],
            position_y=position[1],
            net_name="vbus",
        )
    assert schematic.read_bytes() == before
    rename_net(schematic, workspace_root=tmp_path, net_name="in", new_net_name="vbus")
    add_net_label(
        schematic,
        workspace_root=tmp_path,
        position_x=position[0],
        position_y=position[1],
        net_name="VBUS",
    )


@pytest.mark.parametrize(
    ("net_name", "new_net_name", "message"),
    [
        ("missing", "vbus", "No net labels"),
        ("in", "IN", "must differ"),
        ("in", "GND", "ground net"),
        ("0", "vbus", "ground net"),
    ],
)
def test_invalid_rename_leaves_source_unchanged(
    tmp_path: Path, net_name: str, new_net_name: str, message: str
) -> None:
    schematic = _input_circuit(tmp_path)
    before = schematic.read_bytes()
    with pytest.raises(ValidationError, match=message):
        rename_net(
            schematic,
            workspace_root=tmp_path,
            net_name=net_name,
            new_net_name=new_net_name,
        )
    assert schematic.read_bytes() == before


def test_rename_rejects_existing_destination_before_any_saved_changes(tmp_path: Path) -> None:
    schematic = _input_circuit(tmp_path)
    add_net_label(
        schematic,
        workspace_root=tmp_path,
        position_x=2000,
        position_y=0,
        net_name="VBUS",
    )
    before = schematic.read_bytes()
    output = tmp_path / "rejected.qsch"
    with pytest.raises(ValidationError, match="already exists"):
        rename_net(
            schematic,
            workspace_root=tmp_path,
            net_name="in",
            new_net_name="vbus",
            output_path=output,
        )
    assert schematic.read_bytes() == before
    assert not output.exists()
