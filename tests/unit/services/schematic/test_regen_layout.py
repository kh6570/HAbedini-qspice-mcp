# In the name of God, the Most Gracious, the Most Merciful
"""Regression coverage for the reported three-phase regeneration layout."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qspice_mcp.services._backends._qsch_support import QschTag
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services.schematic.apply_schematic_layout_spec import apply_schematic_layout_spec
from qspice_mcp.services.schematic.check_schematic import check_schematic
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.list_components import list_components
from qspice_mcp.services.simulation._clean_room_netlist import _parse_qsch_schematic
from qspice_mcp.services.workspace.write_workspace_text_file import write_workspace_text_file

_FIXTURE = Path(__file__).resolve().parents[3] / "data" / "schematic" / "regen_layout.json"
_NUMBERED_REFS = ("V1", "B4", "C1", "R4", "R5", "R6", "R7", "V2")


@pytest.mark.parametrize("numbered", [False, True])
def test_regen_layout_preserves_references_and_expression_values(
    tmp_path: Path, *, numbered: bool
) -> None:
    document = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    if numbered:
        for row, reference in zip(document["components"][-8:], _NUMBERED_REFS, strict=True):
            row["reference"] = reference
    spec_path = write_workspace_text_file(
        "regen_layout.json", workspace_root=tmp_path, content=json.dumps(document, indent=2)
    ).output_path
    schematic = create_schematic("regen.qsch", workspace_root=tmp_path).output_path

    result = apply_schematic_layout_spec(schematic, spec_path, workspace_root=tmp_path)
    expected = {row["reference"]: row["value"] for row in document["components"]}
    assert result.applied_count == 26
    catalog = list_components(schematic, workspace_root=tmp_path)
    assert {part.reference: part.value for part in catalog.components} == expected

    editor, _, _ = open_schematic_editor(schematic, workspace_root=tmp_path)
    for reference, value in expected.items():
        assert editor.get_component_value(reference) == value
        assert editor.get_component_parameters(reference)["Value"] == value
    parsed = _parse_qsch_schematic(schematic)[0]
    assert {part.reference: part.value for part in parsed} == expected
    report = check_schematic(schematic, workspace_root=tmp_path)
    assert all(finding.code != "missing_value" for finding in report.findings)

    before = schematic.read_bytes()
    repeated = apply_schematic_layout_spec(schematic, spec_path, workspace_root=tmp_path)
    assert repeated.applied_count == 0
    assert repeated.skipped_existing_count == 26
    assert schematic.read_bytes() == before


def test_empty_value_is_not_replaced_by_extra_symbol_parameter(tmp_path: Path) -> None:
    schematic = create_schematic("empty.qsch", workspace_root=tmp_path).output_path
    spec_path = write_workspace_text_file(
        "layout.json",
        workspace_root=tmp_path,
        content=json.dumps(
            {
                "schema_version": 1,
                "components": [{"reference": "Rload", "component_kind": "resistor", "value": ""}],
            }
        ),
    ).output_path
    apply_schematic_layout_spec(schematic, spec_path, workspace_root=tmp_path)
    editor, _, _ = open_schematic_editor(schematic, workspace_root=tmp_path)
    symbol = editor.get_component("Rload").attributes["symbol_tag"]
    text = QschTag("text", "(0,300)", "1", "0", "0", "0x0", "-1", "-1", '"tc=0.01"')
    symbol.items.append(text)
    editor.save_as(schematic)

    parsed = _parse_qsch_schematic(schematic)[0]
    assert parsed[0].value is None
    assert parsed[0].attributes == ("tc=0.01",)
    report = check_schematic(schematic, workspace_root=tmp_path)
    assert any(finding.code == "missing_value" for finding in report.findings)
