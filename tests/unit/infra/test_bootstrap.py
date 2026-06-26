"""Tests for the ``--setup`` environment readiness report."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.infra.bootstrap import describe_environment_readiness
from qspice_mcp.infra.config import QSpiceSettings

if TYPE_CHECKING:
    from pathlib import Path

_EXPECTED_SECTIONS = {
    "ready",
    "qspice",
    "workspace",
    "dll_build_toolchain",
    "transport",
    "enable_sse",
    "log_folder",
    "recipe_path",
}


def test_describe_environment_readiness_reports_expected_sections(tmp_path: Path) -> None:
    settings = QSpiceSettings(workspace_root=tmp_path)

    report = describe_environment_readiness(settings)

    assert set(report) >= _EXPECTED_SECTIONS
    workspace = report["workspace"]
    assert isinstance(workspace, dict)
    assert workspace["path"] == str(tmp_path.resolve())
    assert workspace["exists"] is True
    assert isinstance(report["qspice"], dict)
    assert isinstance(report["dll_build_toolchain"], dict)
    assert isinstance(report["ready"], bool)


def test_describe_environment_readiness_flags_missing_workspace(tmp_path: Path) -> None:
    settings = QSpiceSettings(workspace_root=tmp_path / "does-not-exist")

    report = describe_environment_readiness(settings)

    workspace = report["workspace"]
    assert isinstance(workspace, dict)
    assert workspace["exists"] is False
    assert report["ready"] is False
