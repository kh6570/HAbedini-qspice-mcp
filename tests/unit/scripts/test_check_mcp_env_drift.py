"""Tests for the MCP launcher env drift guard."""

from __future__ import annotations

from pathlib import Path

from scripts import check_mcp_env_drift as module
from scripts.check_mcp_env_drift import (
    _ENV_TOKEN,
    LAUNCHER_ONLY_ENV,
    _allowed_env_names,
    collect_drift_issues,
)

ROOT = Path(__file__).resolve().parents[3]


def test_mcp_templates_have_no_env_drift() -> None:
    assert collect_drift_issues(root=ROOT) == []


def test_allowed_env_names_include_settings_and_launcher_vars() -> None:
    allowed = _allowed_env_names()
    assert "QSPICE_EXE" in allowed
    assert "QSPICE_LOG_LEVEL" in allowed
    assert allowed >= LAUNCHER_ONLY_ENV
    assert "QSPICE_LOG_FORMAT" not in allowed


def test_env_token_skips_executable_identifiers() -> None:
    tokens = _ENV_TOKEN.findall("QSPICE64.exe sets QSPICE_EXE and QSPICE_DEV_WATCH")
    assert tokens == ["QSPICE_EXE", "QSPICE_DEV_WATCH"]


def test_collect_drift_issues_flags_unknown_token(tmp_path: Path) -> None:
    scanned = Path("scripts/setup_mcp.ps1")
    target = tmp_path / scanned
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('QSPICE_LOG_FORMAT = "console"\n', encoding="utf-8")

    original = module.SCANNED_FILES
    try:
        module.SCANNED_FILES = (scanned,)
        issues = module.collect_drift_issues(root=tmp_path)
    finally:
        module.SCANNED_FILES = original

    assert [issue.token for issue in issues] == ["QSPICE_LOG_FORMAT"]
