"""Tests for normalize_component_text_rotation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.services._backends.schematic_editor import (
    FACTORY_SYMBOL_TEXT_ROTATION_CODE,
    add_simple_component,
    create_blank_schematic_file,
    normalize_component_symbol_text_rotation,
    open_schematic_editor,
    read_component_symbol_metadata,
    set_component_rotation,
    set_component_symbol_text_attributes,
    symbol_text_rotation_code_for_degrees,
)
from qspice_mcp.services.schematic.normalize_component_text_rotation import (
    normalize_component_text_rotation,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_symbol_text_rotation_code_for_degrees() -> None:
    assert symbol_text_rotation_code_for_degrees(0) == 13
    assert symbol_text_rotation_code_for_degrees(90) == 45
    assert symbol_text_rotation_code_for_degrees(270) == 109


def test_normalize_component_symbol_text_compensates_body_rotation(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "rotate.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(800, 400),
        rotation_degrees=0,
    )
    set_component_rotation(editor, reference="R1", rotation_degrees=90)
    editor.save_as(output_path)

    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    rows = normalize_component_symbol_text_rotation(
        reopened,
        reference="R1",
        compensate_component_rotation=True,
    )
    reopened.save_as(output_path)

    assert len(rows) == 2
    assert all(item.updated for item in rows)
    assert all(item.rotation_code == symbol_text_rotation_code_for_degrees(270) for item in rows)

    final, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    metadata = read_component_symbol_metadata(final, reference="R1")
    assert metadata.text_attributes[0].rotation_code == 109
    assert metadata.text_attributes[1].rotation_code == 109


def test_normalize_component_symbol_text_skips_factory_defaults_at_zero_rotation(
    tmp_path: Path,
) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "factory.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(400, 400),
        rotation_degrees=0,
    )
    editor.save_as(output_path)

    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    rows = normalize_component_symbol_text_rotation(
        reopened,
        reference="R1",
        compensate_component_rotation=True,
    )

    assert len(rows) == 2
    assert all(not item.updated for item in rows)
    assert all(item.previous_rotation_code == FACTORY_SYMBOL_TEXT_ROTATION_CODE for item in rows)


def test_normalize_component_symbol_text_updates_non_upright_codes(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "tilted.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(400, 400),
        rotation_degrees=0,
    )
    set_component_symbol_text_attributes(
        editor,
        reference="R1",
        text_role="value",
        rotation_code=45,
    )
    editor.save_as(output_path)

    reopened, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    rows = normalize_component_symbol_text_rotation(
        reopened,
        reference="R1",
        compensate_component_rotation=False,
    )

    value_row = next(item for item in rows if item.role == "value")
    ref_row = next(item for item in rows if item.role == "reference")
    assert value_row.updated is True
    assert value_row.rotation_code == 13
    assert ref_row.updated is False


def test_normalize_component_text_rotation_service(tmp_path: Path) -> None:
    output_path, _ = create_blank_schematic_file(tmp_path / "service.qsch", workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(output_path, workspace_root=tmp_path)
    add_simple_component(
        editor,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position=(800, 400),
        rotation_degrees=0,
    )
    set_component_rotation(editor, reference="R1", rotation_degrees=90)
    editor.save_as(output_path)

    result = normalize_component_text_rotation(
        output_path,
        workspace_root=tmp_path,
        reference="R1",
        text_roles=["refdes", "value"],
    )

    assert result.component_rotation_degrees == 90
    assert result.target_rotation_code == 109
    assert result.updated_count == 2
    assert result.skipped_count == 0


def test_normalize_component_text_rotation_rejects_invalid_role() -> None:
    with pytest.raises(ValueError, match="text_roles"):
        normalize_component_symbol_text_rotation(
            object(),
            reference="R1",
            text_roles=("bad",),
        )
