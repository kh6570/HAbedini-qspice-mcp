"""Tests for the tool metadata casing guard."""

from __future__ import annotations

from pathlib import Path

from scripts import check_tool_metadata_casing as module
from scripts.check_tool_metadata_casing import collect_casing_issues

ROOT = Path(__file__).resolve().parents[3]


def test_tool_metadata_has_no_stale_qspice_prose() -> None:
    assert collect_casing_issues(root=ROOT) == []


def test_collect_casing_issues_flags_stale_prose(tmp_path: Path) -> None:
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir()
    (meta_dir / "example.py").write_text('"documented QSPICE entry points"\n', encoding="utf-8")

    original = module.TOOL_METADATA_DIR
    try:
        module.TOOL_METADATA_DIR = Path("metadata")
        issues = module.collect_casing_issues(root=tmp_path)
    finally:
        module.TOOL_METADATA_DIR = original

    assert len(issues) == 1
    assert issues[0].snippet == '"documented QSPICE entry points"'


def test_casing_guard_allows_qspice_exe_and_qspice64(tmp_path: Path) -> None:
    meta_dir = tmp_path / "metadata"
    meta_dir.mkdir()
    (meta_dir / "example.py").write_text(
        '"when QSPICE_EXE resolves to QSPICE64.exe"\n',
        encoding="utf-8",
    )

    original = module.TOOL_METADATA_DIR
    try:
        module.TOOL_METADATA_DIR = Path("metadata")
        issues = module.collect_casing_issues(root=tmp_path)
    finally:
        module.TOOL_METADATA_DIR = original

    assert issues == []
