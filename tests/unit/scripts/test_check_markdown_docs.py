"""Tests for the markdown doc lint."""

from __future__ import annotations

from pathlib import Path

from scripts.check_markdown_docs import _scan_file, collect_issues

ROOT = Path(__file__).resolve().parents[3]


def _write(tmp_path: Path, rel: str, text: str) -> Path:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return Path(rel)


def test_public_docs_are_clean() -> None:
    assert collect_issues(root=ROOT) == []


def test_detects_table_split_by_blank_line(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "AGENTS.md",
        "| A | B |\n| --- | --- |\n\n| 1 | 2 |\n",
    )
    rules = {issue.rule for issue in _scan_file(rel, root=tmp_path)}
    assert "stray-table-row" in rules


def test_detects_column_mismatch(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "README.md",
        "| A | B |\n| --- | --- |\n| 1 | 2 | 3 |\n",
    )
    rules = {issue.rule for issue in _scan_file(rel, root=tmp_path)}
    assert "table-column-mismatch" in rules


def test_detects_broken_relative_link(tmp_path: Path) -> None:
    rel = _write(tmp_path, "docs/guide.md", "See [missing](./nope.md).\n")
    issues = _scan_file(rel, root=tmp_path)
    assert [issue.rule for issue in issues] == ["broken-link"]


def test_accepts_valid_link_and_table(tmp_path: Path) -> None:
    _write(tmp_path, "docs/other.md", "ok\n")
    rel = _write(
        tmp_path,
        "docs/guide.md",
        "See [other](other.md) and skip [web](https://example.com).\n\n"
        "| A | B |\n| --- | --- |\n| 1 | 2 |\n",
    )
    assert _scan_file(rel, root=tmp_path) == []


def test_ignores_pipes_inside_code_fence(tmp_path: Path) -> None:
    rel = _write(
        tmp_path,
        "docs/guide.md",
        "```\n| not | a | table |\n```\n",
    )
    assert _scan_file(rel, root=tmp_path) == []
