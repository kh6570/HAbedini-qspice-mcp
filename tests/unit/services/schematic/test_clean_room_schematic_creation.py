"""Tests for clean-room schematic creation fallbacks."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.services._backends.clean_room_schematic import (
    blank_schematic_bytes,
    starter_schematic_bytes,
)
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic

if TYPE_CHECKING:
    from pathlib import Path

schematic_edits = importlib.import_module("qspice_mcp.services._backends.schematic_editor_edits")
starter_service = importlib.import_module("qspice_mcp.services.schematic.create_starter_schematic")


def test_create_schematic_falls_back_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "blank.qsch"
    monkeypatch.setattr(schematic_edits, "load_qsch_editor_factory", lambda: (None, None))

    result = create_schematic(output, workspace_root=tmp_path)

    assert result.output_path == output.resolve(strict=False)
    assert result.overwritten is False
    assert output.read_bytes() == blank_schematic_bytes()


def test_create_starter_schematic_falls_back_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = tmp_path / "starter.qsch"
    monkeypatch.setattr(starter_service, "load_qsch_editor_factory", lambda: (None, None))

    result = create_starter_schematic(output, workspace_root=tmp_path)

    payload = output.read_bytes()

    assert result.source_reference == "V1"
    assert result.load_reference == "R1"
    assert result.source_value == "10"
    assert result.load_value == "1k"
    assert b"component (400,400) 0 0" in payload
    assert b"component (800,400) 0 0" in payload
    assert b'wire (400,600) (800,600) "VIN"' in payload
    assert b'net (400,200) 1 13 0 "GND"' in payload
    assert b'net (800,200) 1 13 0 "GND"' in payload
    assert b'wire (400,200) (800,200) "GND"' not in payload
    assert b"\xef\xbb\xbf.op" in payload


def test_starter_schematic_bytes_rejects_duplicate_references() -> None:
    with pytest.raises(ValueError, match="must be distinct"):
        starter_schematic_bytes(
            source_reference="V1",
            source_value="10",
            load_reference="V1",
            load_value="1k",
            input_net_name="VIN",
            analysis_instruction=".op",
        )


def test_starter_schematic_bytes_rejects_multiline_values() -> None:
    with pytest.raises(ValueError, match="must not contain line breaks"):
        starter_schematic_bytes(
            source_reference="V1",
            source_value="10\n20",
            load_reference="R1",
            load_value="1k",
            input_net_name="VIN",
            analysis_instruction=".op",
        )


def test_starter_schematic_bytes_rejects_blank_instruction() -> None:
    with pytest.raises(ValueError, match="analysis_instruction must not be empty"):
        starter_schematic_bytes(
            source_reference="V1",
            source_value="10",
            load_reference="R1",
            load_value="1k",
            input_net_name="VIN",
            analysis_instruction="  ",
        )


def test_create_starter_schematic_fallback_round_trips_with_qspice_when_available(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic_editor = importlib.import_module("qspice_mcp.services._backends.schematic_editor")

    output = tmp_path / "starter-roundtrip.qsch"
    monkeypatch.setattr(starter_service, "load_qsch_editor_factory", lambda: (None, None))

    result = create_starter_schematic(output, workspace_root=tmp_path)

    reopened, _, _ = schematic_editor.open_schematic_editor(
        result.output_path,
        workspace_root=tmp_path,
    )

    assert tuple(str(reference) for reference in reopened.get_components()) == ("V1", "R1")
    assert reopened.get_component_value("V1") == "10"
    assert reopened.get_component_value("R1") == "1k"
