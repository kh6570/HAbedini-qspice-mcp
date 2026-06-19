"""Tests for QSpice capability probing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.adapters.probe import build_summary, clear_probe_cache, probe_qspice
from qspice_mcp.infra.config import QSpiceSettings

if TYPE_CHECKING:
    from pathlib import Path


def test_probe_prefers_configured_executable(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    result = probe_qspice(QSpiceSettings(exe=executable))

    assert result.configured is True
    assert result.source == "configured"
    assert result.executable == executable.resolve()
    assert result.exists is True


def test_probe_falls_back_to_path(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.default_install_locations", lambda: ())
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.which", lambda _: str(executable))

    result = probe_qspice(QSpiceSettings())

    assert result.configured is False
    assert result.source == "path"
    assert result.executable == executable.resolve()


def test_probe_falls_back_to_default_install_location(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setattr(
        "qspice_mcp.adapters.probe.default_install_locations",
        lambda: (executable,),
    )
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.which", lambda _: None)

    result = probe_qspice(QSpiceSettings())

    assert result.configured is False
    assert result.source == "default-location"
    assert result.executable == executable.resolve()


def test_probe_uses_metadata_before_cli_on_windows(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    calls: list[str] = []
    typed_monkeypatch = monkeypatch

    def fake_metadata(path: Path) -> tuple[str | None, str]:
        calls.append("metadata")
        return "1.2.3.4", "metadata"

    def fake_cli(path: Path) -> tuple[str | None, str]:
        calls.append("cli")
        return "9.9.9.9", "cli"

    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.sys.platform", "win32")
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe._detect_version_metadata", fake_metadata)
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe._detect_version_cli", fake_cli)

    result = probe_qspice(QSpiceSettings(exe=executable))

    assert result.version == "1.2.3.4"
    assert result.version_source == "metadata"
    assert calls == ["metadata"]


def test_probe_skips_cli_when_disabled(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_PROBE_SKIP_CLI", "1")
    typed_monkeypatch.setattr(
        "qspice_mcp.adapters.probe._detect_version_metadata",
        lambda _path: (None, "unavailable"),
    )
    typed_monkeypatch.setattr(
        "qspice_mcp.adapters.probe._detect_version_cli",
        lambda _path: (_ for _ in ()).throw(AssertionError("cli should not run")),
    )

    result = probe_qspice(QSpiceSettings(exe=executable))

    assert result.version_source == "timestamp"


def test_build_summary_is_json_ready(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    summary = build_summary(QSpiceSettings(exe=executable))

    assert summary["configured"] is True
    assert summary["executable"] == str(executable.resolve())
    assert summary["exists"] is True


def test_probe_is_memoized_for_same_executable(monkeypatch: object, tmp_path: Path) -> None:
    clear_probe_cache()
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    calls: list[str] = []
    typed_monkeypatch = monkeypatch

    def fake_metadata(path: Path) -> tuple[str | None, str]:
        del path
        calls.append("metadata")
        return "1.2.3.4", "metadata"

    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.sys.platform", "win32")
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe._detect_version_metadata", fake_metadata)
    typed_monkeypatch.setattr(
        "qspice_mcp.adapters.probe._detect_version_cli",
        lambda _path: (_ for _ in ()).throw(AssertionError("cli should not run")),
    )

    settings = QSpiceSettings(exe=executable)
    first = probe_qspice(settings)
    second = probe_qspice(settings)

    assert first.version == second.version == "1.2.3.4"
    assert calls == ["metadata"]


def test_probe_cache_invalidates_when_executable_mtime_changes(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    clear_probe_cache()
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    calls: list[str] = []
    typed_monkeypatch = monkeypatch

    def fake_metadata(path: Path) -> tuple[str | None, str]:
        del path
        calls.append("metadata")
        return f"v{len(calls)}", "metadata"

    typed_monkeypatch.setattr("qspice_mcp.adapters.probe.sys.platform", "win32")
    typed_monkeypatch.setattr("qspice_mcp.adapters.probe._detect_version_metadata", fake_metadata)
    typed_monkeypatch.setattr(
        "qspice_mcp.adapters.probe._detect_version_cli",
        lambda _path: (_ for _ in ()).throw(AssertionError("cli should not run")),
    )

    settings = QSpiceSettings(exe=executable)
    first = probe_qspice(settings)
    executable.write_text("updated", encoding="utf-8")
    second = probe_qspice(settings)

    assert first.version == "v1"
    assert second.version == "v2"
    assert calls == ["metadata", "metadata"]
