"""Tests for the PinDef-style batch `.DLL` device creation service."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._backends.clean_room_schematic import blank_schematic_bytes
from qspice_mcp.services.mixed_signal.create_dll_device_from_spec import (
    DEVICE_SPEC_SCHEMA_VERSION,
    create_dll_device_from_spec,
)
from qspice_mcp.services.mixed_signal.describe_device_spec import describe_device_spec

if TYPE_CHECKING:
    from pathlib import Path

_ATTINY_PINS = [
    {"name": "PB0", "direction": "input"},
    {"name": "PB1", "direction": "output"},
    {"name": "PB2", "direction": "input"},
    {"name": "PB3", "direction": "output"},
    {"name": "PB4", "direction": "output"},
]


def _make_blank_schematic(workspace: Path, name: str = "device.qsch") -> Path:
    schematic = workspace / name
    schematic.write_bytes(blank_schematic_bytes())
    return schematic


def test_create_dll_device_from_inline_pins_places_block_and_scaffolds(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)

    result = create_dll_device_from_spec(
        schematic,
        workspace_root=workspace,
        settings=None,
        reference="X1",
        device_name="ATTINY85",
        pins=_ATTINY_PINS,
    )

    assert result.reference == "X1"
    assert result.device_name == "ATTINY85"
    assert result.input_pin_names == ("PB0", "PB2")
    assert result.output_pin_names == ("PB1", "PB3", "PB4")
    assert tuple(pin.name for pin in result.pins) == ("PB0", "PB1", "PB2", "PB3", "PB4")
    assert result.spec_path is None

    # Scaffolded source matches the placed symbol contract.
    assert result.source_path is not None
    assert result.cmake_path is not None
    assert result.export_name == "ATTINY85"
    source_text = result.source_path.read_text(encoding="utf-8")
    assert 'extern "C" __declspec(dllexport) void ATTINY85' in source_text
    assert "double PB0 = data[0].d; // input" in source_text
    assert "struct sATTINY85" in source_text

    assert result.output_path.is_file()


def test_create_dll_device_from_spec_file_without_scaffold(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)
    spec_file = workspace / "attiny85.pindef.json"
    spec_file.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "device_name": "ATTINY85",
                "description": "ATtiny25/45/85 pin map",
                "pins": _ATTINY_PINS,
            }
        ),
        encoding="utf-8",
    )

    result = create_dll_device_from_spec(
        schematic,
        workspace_root=workspace,
        settings=None,
        reference="X2",
        spec_path=spec_file,
        scaffold_source=False,
    )

    assert result.device_name == "ATTINY85"
    assert result.description == "ATtiny25/45/85 pin map"
    assert result.spec_path == spec_file.resolve(strict=False)
    assert result.input_pin_names == ("PB0", "PB2")
    assert result.output_pin_names == ("PB1", "PB3", "PB4")
    assert result.source_path is None
    assert result.cmake_path is None
    assert any("scaffold skipped" in note.lower() for note in result.notes)


def test_create_dll_device_from_spec_rejects_both_input_modes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)
    spec_file = workspace / "spec.json"
    spec_file.write_text(json.dumps({"device_name": "D", "pins": _ATTINY_PINS}), encoding="utf-8")

    with pytest.raises(ValidationError, match="not both"):
        create_dll_device_from_spec(
            schematic,
            workspace_root=workspace,
            settings=None,
            reference="X1",
            pins=_ATTINY_PINS,
            spec_path=spec_file,
        )


def test_create_dll_device_from_spec_requires_pins_or_spec(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)

    with pytest.raises(ValidationError, match="pins array inline or a spec_path"):
        create_dll_device_from_spec(
            schematic,
            workspace_root=workspace,
            settings=None,
            reference="X1",
            device_name="ATTINY85",
        )


@pytest.mark.parametrize(
    ("pins", "match"),
    [
        ([{"name": "PB0", "direction": "sideways"}], "unsupported direction"),
        ([{"name": "", "direction": "input"}], "non-empty string name"),
        ([{"name": "PB0", "direction": "input"}, {"name": "PB0", "direction": "output"}], "unique"),
        ([], "non-empty pins array"),
    ],
)
def test_create_dll_device_from_spec_validates_pins(
    tmp_path: Path,
    pins: list[dict[str, object]],
    match: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)

    with pytest.raises(ValidationError, match=match):
        create_dll_device_from_spec(
            schematic,
            workspace_root=workspace,
            settings=None,
            reference="X1",
            device_name="ATTINY85",
            pins=pins,
        )


def test_describe_device_spec_returns_v1_schema_and_example() -> None:
    description = describe_device_spec()

    assert description.schema_version == DEVICE_SPEC_SCHEMA_VERSION
    assert description.pin_directions == ("input", "output")
    assert description.bundled_example_path == "attiny85.v1.json"
    assert description.json_schema["required"] == ["device_name", "pins"]
    assert description.example_document["schema_version"] == DEVICE_SPEC_SCHEMA_VERSION
    assert description.example_document["device_name"] == "ATTINY85"
    assert len(description.example_document["pins"]) >= 1
    assert any("create_dll_device_from_spec" in note for note in description.notes)


def test_bundled_example_device_spec_is_accepted_by_create_tool(tmp_path: Path) -> None:
    """The shipped example document must stay valid input for the create tool."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)
    spec_file = workspace / "example.pindef.json"
    spec_file.write_text(json.dumps(describe_device_spec().example_document), encoding="utf-8")

    result = create_dll_device_from_spec(
        schematic,
        workspace_root=workspace,
        settings=None,
        reference="X1",
        spec_path=spec_file,
        scaffold_source=False,
    )

    assert result.device_name == "ATTINY85"
    assert result.input_pin_names == ("PB0", "PB1", "PB2")
    assert result.output_pin_names == ("PB3", "PB4")


def test_create_dll_device_from_spec_rejects_unknown_schema_version(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    schematic = _make_blank_schematic(workspace)
    spec_file = workspace / "spec.json"
    spec_file.write_text(
        json.dumps({"schema_version": 2, "device_name": "D", "pins": _ATTINY_PINS}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="schema_version"):
        create_dll_device_from_spec(
            schematic,
            workspace_root=workspace,
            settings=None,
            reference="X1",
            spec_path=spec_file,
        )
