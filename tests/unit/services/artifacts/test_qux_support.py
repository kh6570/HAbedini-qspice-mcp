"""Tests for companion QUX export-support reporting."""

from __future__ import annotations

import importlib

from qspice_mcp.adapters.probe import ProbeResult
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.artifacts.describe_qux_export_support import describe_qux_export_support

qux_service = importlib.import_module("qspice_mcp.services.artifacts.describe_qux_export_support")


def test_describe_qux_export_support_reports_available_companion(monkeypatch, tmp_path) -> None:
    qspice_executable = tmp_path / "QSPICE64.exe"
    qux_executable = tmp_path / "QUX.exe"
    qspice_executable.write_text("", encoding="utf-8")
    qux_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_service,
        "probe_qspice",
        lambda settings: ProbeResult(
            configured=True,
            executable=qspice_executable,
            exists=True,
            source="configured",
            version="1.2.3",
            version_source="cli",
            note="",
        ),
    )

    support = describe_qux_export_support(
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path)
    )

    assert support.available is True
    assert support.supports_export is True
    assert support.supported_export_formats == ("CSV", "ASCII", "SPICE", "S2P")
    assert support.qux_path == qux_executable.resolve(strict=False)


def test_describe_qux_export_support_reports_missing_companion(monkeypatch, tmp_path) -> None:
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_service,
        "probe_qspice",
        lambda settings: ProbeResult(
            configured=True,
            executable=qspice_executable,
            exists=True,
            source="configured",
            version=None,
            version_source="unavailable",
            note="",
        ),
    )

    support = describe_qux_export_support(
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path)
    )

    assert support.available is False
    assert support.qux_path == (tmp_path / "QUX.exe").resolve(strict=False)
    assert support.notes == (
        "QSpice is available, but companion QUX.exe was not found next to it.",
    )
