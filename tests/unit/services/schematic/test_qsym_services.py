"""Tests for standalone `.qsym` symbol export and import services."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import QSpiceError, ValidationError
from qspice_mcp.services._backends.clean_room_schematic import blank_schematic_bytes
from qspice_mcp.services._backends.schematic_editor import (
    open_schematic_editor,
    read_component_symbol_metadata,
    read_qsym_symbol_tag,
)
from qspice_mcp.services.schematic.add_component_from_qsym import add_component_from_qsym
from qspice_mcp.services.schematic.add_dll_block import add_dll_block
from qspice_mcp.services.schematic.export_symbol_to_qsym import export_symbol_to_qsym

if TYPE_CHECKING:
    from pathlib import Path

_QSCH_BINARY_PREFIX = b"\xff\xd8\xff\xdb"


def _make_dll_schematic(workspace: Path, name: str = "device.qsch") -> Path:
    schematic = workspace / name
    schematic.write_bytes(blank_schematic_bytes())
    add_dll_block(
        schematic,
        workspace_root=workspace,
        reference="X1",
        device_name="ATTINY85",
        input_pin_names=("PB0", "PB1", "PB2"),
        output_pin_names=("PB3", "PB4"),
    )
    return schematic


def test_export_symbol_to_qsym_writes_standalone_symbol(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_dll_schematic(workspace)

    result = export_symbol_to_qsym(
        schematic,
        workspace_root=workspace,
        reference="X1",
    )

    assert result.symbol_name == "ATTINY85"
    assert result.output_path == (workspace / "ATTINY85.qsym").resolve(strict=False)
    assert result.pin_names == ("PB0", "PB1", "PB2", "PB3", "PB4")
    assert result.byte_count > 0

    raw = result.output_path.read_bytes()
    assert raw.startswith(_QSCH_BINARY_PREFIX)
    text = raw[4:].decode("latin-1")
    assert text.startswith("\xabsymbol ATTINY85")
    assert '"PB0"' in text

    tag = read_qsym_symbol_tag(result.output_path)
    assert tag.tag == "symbol"
    assert str(tag.tokens[1]) == "ATTINY85"
    assert len(tag.get_items("pin")) == 5


def test_export_symbol_to_qsym_honors_custom_name_and_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_dll_schematic(workspace)
    output = workspace / "lib" / "tiny.qsym"

    result = export_symbol_to_qsym(
        schematic,
        workspace_root=workspace,
        reference="X1",
        output_path=output,
        symbol_name="Tiny 85",
    )

    assert result.symbol_name == "Tiny_85"
    assert result.output_path == output.resolve(strict=False)
    assert output.is_file()


def test_add_component_from_qsym_round_trips_symbol(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source_schematic = _make_dll_schematic(workspace)
    exported = export_symbol_to_qsym(
        source_schematic,
        workspace_root=workspace,
        reference="X1",
    )

    target = workspace / "target.qsch"
    target.write_bytes(blank_schematic_bytes())

    result = add_component_from_qsym(
        target,
        workspace_root=workspace,
        qsym_path=exported.output_path,
        reference="X7",
        position_x=400,
        position_y=-200,
    )

    assert result.reference == "X7"
    assert result.symbol_name == "ATTINY85"
    assert result.pin_names == ("PB0", "PB1", "PB2", "PB3", "PB4")
    assert result.qsym_path == exported.output_path

    # The persisted schematic must expose the embedded symbol again.
    editor, _, _ = open_schematic_editor(result.output_path, workspace_root=workspace)
    metadata = read_component_symbol_metadata(editor, reference="X7")
    assert tuple(pin.name for pin in metadata.pins) == ("PB0", "PB1", "PB2", "PB3", "PB4")
    assert metadata.type_name == "\u00d8(.DLL)"


def test_add_component_from_qsym_preserves_inline_library_payload(tmp_path: Path) -> None:
    """Externally generated `.qsym` files with pipe-delimited payloads survive import.

    QSpice inlines subcircuit text into the symbol as ``«library file:
    |.subckt ...|»``; the payload contains spaces (and runs of spaces) that
    must round-trip exactly, and the two-word tag name must stay intact.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    payload = "|.subckt MYDEV a b\\nR1 a b  1k\\n.ends MYDEV|"
    qsym_text = (
        "\xabsymbol MYDEV\n"
        "  \xabtype: X\xbb\n"
        '  \xabdescription: "Clean-room test device"\xbb\n'
        "  \xabshorted pins: false\xbb\n"
        f"  \xablibrary file: {payload}\xbb\n"
        "  \xabrect (-400,300) (400,-300) 0 0 0 0x1000000 0x0 -1 0 -1\xbb\n"
        '  \xabtext (0,350) 1 7 0 0x1000000 -1 -1 "X1"\xbb\n'
        '  \xabtext (0,-350) 1 7 0 0x1000000 -1 -1 "MYDEV"\xbb\n'
        '  \xabpin (-400,100) (0,0) 1 0 0 0x1000000 -1 "a"\xbb\n'
        '  \xabpin (-400,-100) (0,0) 1 0 0 0x1000000 -1 "b"\xbb\n'
        "\xbb\n"
    )
    qsym = workspace / "mydev.qsym"
    qsym.write_bytes(_QSCH_BINARY_PREFIX + qsym_text.encode("latin-1"))

    tag = read_qsym_symbol_tag(qsym)
    library_items = tag.get_items("library file:")
    assert [item.tag for item in tag.items[:4]] == [
        "type:",
        "description:",
        "shorted pins:",
        "library file:",
    ]
    assert len(library_items) == 1
    assert library_items[0].tokens[1] == payload

    target = workspace / "target.qsch"
    target.write_bytes(blank_schematic_bytes())
    result = add_component_from_qsym(
        target,
        workspace_root=workspace,
        qsym_path=qsym,
        reference="X9",
    )

    assert result.symbol_name == "MYDEV"
    assert result.library_file == payload
    assert result.pin_names == ("a", "b")

    editor, _, _ = open_schematic_editor(result.output_path, workspace_root=workspace)
    metadata = read_component_symbol_metadata(editor, reference="X9")
    assert metadata.library_file == payload
    assert metadata.shorted_pins is False

    saved_text = result.output_path.read_bytes().decode("latin-1")
    assert f"\xablibrary file: {payload}\xbb" in saved_text


def test_add_component_from_qsym_rejects_wrong_suffix(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "target.qsch"
    target.write_bytes(blank_schematic_bytes())
    not_a_symbol = workspace / "note.txt"
    not_a_symbol.write_text("hello", encoding="utf-8")

    with pytest.raises(ValidationError, match=r"\.qsym"):
        add_component_from_qsym(
            target,
            workspace_root=workspace,
            qsym_path=not_a_symbol,
            reference="X1",
        )


def test_read_qsym_symbol_tag_rejects_non_symbol_content(tmp_path: Path) -> None:
    bogus = tmp_path / "bogus.qsym"
    bogus.write_bytes(_QSCH_BINARY_PREFIX + "\xabschematic\n\xbb\n".encode("latin-1"))

    with pytest.raises(QSpiceError, match="does not contain a QSpice symbol tag"):
        read_qsym_symbol_tag(bogus)
