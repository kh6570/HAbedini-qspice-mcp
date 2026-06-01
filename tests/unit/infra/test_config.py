"""Tests for runtime settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.infra.config import QSpiceSettings, build_settings

if TYPE_CHECKING:
    from pathlib import Path


def test_settings_read_executable_from_environment(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_EXE", str(executable))

    settings = QSpiceSettings().normalized()

    assert settings.exe == executable.resolve()


def test_settings_derive_cache_dir_when_not_configured(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.delenv("QSPICE_CACHE_DIR", raising=False)
    typed_monkeypatch.delenv("QSPICE_EXE", raising=False)

    settings = QSpiceSettings().normalized()

    assert settings.cache_dir is not None


def test_settings_read_telemetry_flag_from_environment(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_TELEMETRY_ENABLED", "true")

    settings = QSpiceSettings().normalized()

    assert settings.telemetry_enabled is True


def test_build_settings_applies_cli_overrides(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    executable = workspace_root / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    settings = build_settings(
        transport="sse",
        exe=executable,
        workspace_root=workspace_root,
        telemetry_enabled=True,
    )

    assert settings.transport == "sse"
    assert settings.exe == executable.resolve()
    assert settings.workspace_root == workspace_root.resolve()
    assert settings.telemetry_enabled is True
