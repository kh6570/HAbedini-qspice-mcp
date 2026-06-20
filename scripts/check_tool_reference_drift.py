#!/usr/bin/env python3
"""Assert docs/tool_reference.md matches the live registered MCP tool set.

Checks:
- summary table rows (``| `tool_name` |``) match implemented tools exactly
- one ``## tool_name`` detail section per tool, with no duplicates
- table rows and detail sections stay in sync with each other
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry, build_tool_registry

TOOL_REFERENCE = Path("docs/tool_reference.md")

_TABLE_ROW = re.compile(r"^\| `([^`]+)` \|", re.MULTILINE)
_DETAIL_SECTION = re.compile(r"^## (.+)$", re.MULTILINE)
# Implemented MCP tools use snake_case identifiers; prose doc sections do not.
_TOOL_SECTION_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class DriftIssue:
    category: str
    detail: str


def _live_tool_names() -> frozenset[str]:
    tools = build_tool_registry()
    registered = build_runtime_tool_registry(tools)
    return frozenset(tool.name for tool in registered)


def _parse_table_tools(text: str) -> tuple[frozenset[str], list[str]]:
    names = _TABLE_ROW.findall(text)
    duplicates = sorted({name for name in names if names.count(name) > 1})
    return frozenset(names), duplicates


def _parse_detail_sections(text: str) -> tuple[frozenset[str], list[str]]:
    names = [
        match.group(1)
        for match in _DETAIL_SECTION.finditer(text)
        if _TOOL_SECTION_NAME.fullmatch(match.group(1))
    ]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    return frozenset(names), duplicates


def _sorted_diff(label: str, left: frozenset[str], right: frozenset[str]) -> DriftIssue | None:
    missing = sorted(right - left)
    if not missing:
        return None
    return DriftIssue(category=label, detail=", ".join(missing))


def collect_drift_issues(*, root: Path) -> list[DriftIssue]:
    path = root / TOOL_REFERENCE
    if not path.is_file():
        return [DriftIssue("missing-doc", str(TOOL_REFERENCE))]

    text = path.read_text(encoding="utf-8")
    live = _live_tool_names()
    table, table_dupes = _parse_table_tools(text)
    sections, section_dupes = _parse_detail_sections(text)

    issues: list[DriftIssue] = []
    for category, duplicates in (
        ("duplicate-table-row", table_dupes),
        ("duplicate-detail-section", section_dupes),
    ):
        if duplicates:
            issues.append(DriftIssue(category=category, detail=", ".join(duplicates)))

    for label, left, right in (
        ("live-tool-missing-from-table", table, live),
        ("stale-table-row", live, table),
        ("live-tool-missing-detail-section", sections, live),
        ("stale-detail-section", live, sections),
        ("table-row-missing-detail-section", sections, table),
        ("detail-section-missing-table-row", table, sections),
    ):
        issue = _sorted_diff(label, left, right)
        if issue is not None:
            issues.append(issue)

    return issues


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    issues = collect_drift_issues(root=root)
    if issues:
        print(
            f"ERROR: Found {len(issues)} tool-reference drift issue(s) in {TOOL_REFERENCE}:",
            file=sys.stderr,
        )
        for item in issues:
            print(f"  - [{item.category}] {item.detail}", file=sys.stderr)
        return 1

    live_count = len(_live_tool_names())
    print(
        f"OK: {TOOL_REFERENCE} summary table and detail sections match "
        f"{live_count} live registered tool(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
