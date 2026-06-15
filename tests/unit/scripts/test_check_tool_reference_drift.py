"""Tests for the tool-reference drift guard."""

from __future__ import annotations

from pathlib import Path

from scripts.check_tool_reference_drift import (
    _parse_detail_sections,
    _parse_table_tools,
    collect_drift_issues,
)

ROOT = Path(__file__).resolve().parents[3]


def test_tool_reference_matches_live_registry() -> None:
    issues = collect_drift_issues(root=ROOT)
    assert issues == []


def test_parse_table_tools_detects_duplicate_rows() -> None:
    text = "| `run_simulation` | implemented | x |\n| `run_simulation` | implemented | y |\n"
    names, duplicates = _parse_table_tools(text)
    assert names == frozenset({"run_simulation"})
    assert duplicates == ["run_simulation"]


def test_parse_detail_sections_ignores_prose_headings() -> None:
    text = "## run_simulation\n\nbody\n\n## Future Extension Points\n"
    names, duplicates = _parse_detail_sections(text)
    assert names == frozenset({"run_simulation"})
    assert duplicates == []


def test_parse_detail_sections_detects_duplicate_sections() -> None:
    text = "## run_simulation\n\na\n\n## run_simulation\n"
    names, duplicates = _parse_detail_sections(text)
    assert names == frozenset({"run_simulation"})
    assert duplicates == ["run_simulation"]
