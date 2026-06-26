"""Tests for the compare_schematics service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.compare_schematics import compare_schematics
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic

if TYPE_CHECKING:
    from pathlib import Path


def test_compare_schematics_detects_value_change(tmp_path: Path) -> None:
    base = tmp_path / "base.qsch"
    revised = tmp_path / "revised.qsch"
    create_starter_schematic(base, workspace_root=tmp_path, load_value="1k")
    create_starter_schematic(revised, workspace_root=tmp_path, load_value="2k")

    comparison = compare_schematics(base, revised, workspace_root=tmp_path)

    assert comparison.identical is False
    changed_fields = {(change.reference, change.field) for change in comparison.changed_components}
    assert ("R1", "value") in changed_fields
    value_change = next(
        change for change in comparison.changed_components if change.field == "value"
    )
    assert value_change.base == "1k"
    assert value_change.revised == "2k"


def test_compare_schematics_reports_identical(tmp_path: Path) -> None:
    base = tmp_path / "base.qsch"
    revised = tmp_path / "revised.qsch"
    create_starter_schematic(base, workspace_root=tmp_path)
    create_starter_schematic(revised, workspace_root=tmp_path)

    comparison = compare_schematics(base, revised, workspace_root=tmp_path)

    assert comparison.added_components == ()
    assert comparison.removed_components == ()
    assert comparison.changed_components == ()
    assert comparison.identical is True
