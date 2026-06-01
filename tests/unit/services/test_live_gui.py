"""Tests for live GUI support services."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path  # noqa: TC003

import pytest

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.live_gui.describe_live_gui_support import describe_live_gui_support
from qspice_mcp.services.live_gui.open_schematic_in_gui import open_schematic_in_gui
from qspice_mcp.services.live_gui.refresh_schematic_in_gui import refresh_schematic_in_gui
from qspice_mcp.services.live_gui.scaffold_live_gui_session import scaffold_live_gui_session

open_schematic_module = importlib.import_module(
    "qspice_mcp.services.live_gui.open_schematic_in_gui"
)
refresh_schematic_module = importlib.import_module(
    "qspice_mcp.services.live_gui.refresh_schematic_in_gui"
)


def test_describe_live_gui_support_reports_optional_layer_state(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    settings = QSpiceSettings(exe=executable, workspace_root=tmp_path)

    result = describe_live_gui_support(settings=settings)

    assert result.windows_only is True
    assert result.platform_supported is (sys.platform == "win32")
    assert result.version_gated is True
    assert result.external_bridge_required is True
    assert result.session_manifest_scaffolding is True
    assert result.qspice_executable_configured is True
    assert any("scaffold_live_gui_session" in note for note in result.notes)


def test_scaffold_live_gui_session_writes_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    executable = workspace / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = workspace / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    result = scaffold_live_gui_session(
        "buck-debug",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=executable, workspace_root=workspace),
        schematic_path=schematic,
        waveform_names=("V(out)", "I(L1)"),
        cross_probe_signals=("V(out)",),
    )

    assert result.session_name == "buck-debug"
    assert result.manifest_path.is_file()
    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.launch_command == (
        str(executable.resolve(strict=False)),
        str(schematic.resolve(strict=False)),
    )
    assert result.waveform_names == ("V(out)", "I(L1)")
    assert result.cross_probe_signals == ("V(out)",)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["session_name"] == "buck-debug"
    assert manifest["transport"] == "windows_messages"
    assert manifest["bridge_protocol"]["command_queue"]["path"].endswith("bridge.commands.jsonl")
    assert manifest["bridge_protocol"]["event_log"]["path"].endswith("bridge.events.jsonl")
    assert manifest["launch"]["command"][0].endswith("QSPICE64.exe")
    assert manifest["waveform_names"] == ["V(out)", "I(L1)"]


def test_scaffold_live_gui_session_rejects_empty_name(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="session_name"):
        scaffold_live_gui_session(
            " ",
            workspace_root=workspace,
            settings=QSpiceSettings(workspace_root=workspace),
        )


def test_open_schematic_in_gui_uses_windows_file_association(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    started_paths: list[str] = []

    monkeypatch.setattr(open_schematic_module.sys, "platform", "win32")
    monkeypatch.setattr(
        open_schematic_module.os,
        "startfile",
        lambda path: started_paths.append(path),  # noqa: PLW0108
        raising=False,
    )

    result = open_schematic_in_gui("demo.qsch", workspace_root=tmp_path)

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.launcher == "os_file_association"
    assert result.started is True
    assert started_paths == [str(schematic.resolve(strict=False))]


def test_open_schematic_in_gui_requires_windows_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    monkeypatch.setattr(open_schematic_module.sys, "platform", "linux")

    with pytest.raises(BackendUnavailableError, match="only available on Windows"):
        open_schematic_in_gui(schematic, workspace_root=tmp_path)


def test_refresh_schematic_in_gui_reopens_without_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    started_paths: list[str] = []

    monkeypatch.setattr(refresh_schematic_module.sys, "platform", "win32")
    monkeypatch.setattr(
        refresh_schematic_module.os,
        "startfile",
        lambda path: started_paths.append(path),  # noqa: PLW0108
        raising=False,
    )

    result = refresh_schematic_in_gui(
        "demo.qsch",
        workspace_root=tmp_path,
        settings=QSpiceSettings(workspace_root=tmp_path),
    )

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.strategy == "reopen_via_association"
    assert result.qspice_process_restart_requested is False
    assert result.qspice_process_restart_exit_code is None
    assert result.started is True
    assert started_paths == [str(schematic.resolve(strict=False))]


def test_refresh_schematic_in_gui_restart_requires_force_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    monkeypatch.setattr(refresh_schematic_module.sys, "platform", "win32")

    with pytest.raises(ValueError, match="requires force_restart=true"):
        refresh_schematic_in_gui(
            schematic,
            workspace_root=tmp_path,
            settings=QSpiceSettings(workspace_root=tmp_path),
            strategy="restart_qspice_and_reopen",
        )


def test_refresh_schematic_in_gui_restart_runs_taskkill_then_reopens(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    started_paths: list[str] = []
    taskkill_calls: list[list[str]] = []

    monkeypatch.setattr(refresh_schematic_module.sys, "platform", "win32")
    monkeypatch.setattr(
        refresh_schematic_module.os,
        "startfile",
        lambda path: started_paths.append(path),  # noqa: PLW0108
        raising=False,
    )

    def fake_run(args: list[str], **_: object) -> object:
        taskkill_calls.append(args)
        return __import__("subprocess").CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(refresh_schematic_module.subprocess, "run", fake_run)

    result = refresh_schematic_in_gui(
        schematic,
        workspace_root=tmp_path,
        settings=QSpiceSettings(workspace_root=tmp_path, exe=executable),
        strategy="restart_qspice_and_reopen",
        force_restart=True,
    )

    assert result.strategy == "restart_qspice_and_reopen"
    assert result.qspice_process_restart_requested is True
    assert result.qspice_process_restart_exit_code == 0
    assert taskkill_calls == [["taskkill", "/F", "/IM", "QSPICE64.exe"]]
    assert started_paths == [str(schematic.resolve(strict=False))]
