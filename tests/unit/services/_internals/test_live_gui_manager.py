"""Tests for live GUI bridge lifecycle management."""

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.infra.config import QSpiceSettings

live_gui_manager_service = importlib.import_module(
    "qspice_mcp.services._internals.live_gui_manager"
)

if TYPE_CHECKING:
    from qspice_mcp.services._internals.live_gui_manager import LiveGuiSessionManager
    from qspice_mcp.services.live_gui.poll_live_gui_session import LiveGuiSessionStatus
    from qspice_mcp.services.live_gui.poll_live_gui_session_events import LiveGuiSessionEventPoll


def _normalize_path_string(value: str) -> str:
    return str(Path(value).resolve(strict=False)).casefold()


def _write_bridge_script(path: Path, *, exit_immediately: bool) -> Path:
    body = [
        "from __future__ import annotations",
        "import datetime",
        "import json",
        "import pathlib",
        "import sys",
        "import time",
        "manifest_path = pathlib.Path(sys.argv[1])",
        "payload = json.loads(manifest_path.read_text(encoding='utf-8'))",
        "bridge_protocol = payload.get('bridge_protocol', {})",
        "commands_path = pathlib.Path(",
        "    bridge_protocol.get('command_queue', {}).get('path')",
        "    or (manifest_path.parent / 'bridge.commands.jsonl')",
        ")",
        "events_path = pathlib.Path(",
        "    bridge_protocol.get('event_log', {}).get('path')",
        "    or (manifest_path.parent / 'bridge.events.jsonl')",
        ")",
        "(manifest_path.parent / 'bridge.ready').write_text(",
        "    payload['session_name'],",
        "    encoding='utf-8',",
        ")",
    ]
    if exit_immediately:
        body.append("sys.exit(0)")
    else:
        body.extend(
            [
                "processed = 0",
                "sequence = 0",
                "while True:",
                "    commands_path.parent.mkdir(parents=True, exist_ok=True)",
                "    events_path.parent.mkdir(parents=True, exist_ok=True)",
                "    if commands_path.is_file():",
                "        lines = [",
                "            line",
                "            for line in commands_path.read_text(encoding='utf-8').splitlines()",
                "            if line.strip()",
                "        ]",
                "        for raw_command in lines[processed:]:",
                "            command = json.loads(raw_command)",
                "            sequence += 1",
                "            command_payload = command.get('payload', {})",
                "            event_name = 'command_ack'",
                "            if command.get('command') == 'run_netlist':",
                "                event_name = 'run_netlist_complete'",
                "                for key in ('log_path', 'raw_path'):",
                "                    target = command_payload.get(key)",
                "                    if target:",
                "                        target_path = pathlib.Path(target)",
                "                        target_path.parent.mkdir(parents=True, exist_ok=True)",
                "                        target_path.write_text('ok', encoding='utf-8')",
                "            event = {",
                "                'sequence': sequence,",
                "                'event': event_name,",
                "                'command_id': command.get('command_id'),",
                "                'command': command.get('command'),",
                "                'signal': command.get('signal'),",
                "                'payload': command_payload,",
                "                'created_at': datetime.datetime.now().astimezone().isoformat(),",
                "            }",
                "            with events_path.open('a', encoding='utf-8') as handle:",
                "                handle.write(json.dumps(event) + '\\n')",
                "        processed = len(lines)",
                "    time.sleep(0.05)",
            ]
        )
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _wait_for_terminal_status(
    manager: LiveGuiSessionManager,
    session_id: str,
    *,
    deadline_s: float = 5.0,
) -> LiveGuiSessionStatus:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        status = manager.poll_live_gui_session(session_id)
        if status.status in {"completed", "failed", "closed"}:
            return status
        time.sleep(0.05)
    raise AssertionError("Live GUI session did not reach a terminal state in time.")


def _wait_for_file(path: Path, *, deadline_s: float = 5.0) -> None:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {path.name}.")


def _wait_for_live_gui_events(
    manager: LiveGuiSessionManager,
    session_id: str,
    *,
    after_sequence: int = 0,
    deadline_s: float = 5.0,
) -> LiveGuiSessionEventPoll:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        events = manager.poll_live_gui_session_events(session_id, after_sequence=after_sequence)
        if events.events:
            return events
        time.sleep(0.05)
    raise AssertionError("Live GUI bridge did not emit an event in time.")


def test_live_gui_manager_launches_polls_and_closes_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    bridge_script = _write_bridge_script(tmp_path / "bridge.py", exit_immediately=False)

    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )

    launched = manager.launch_live_gui_session(
        session_name="buck-debug",
        schematic_path=str(schematic),
        waveform_names=["V(out)"],
        cross_probe_signals=["I(L1)"],
    )
    ready_path = launched.output_root / "bridge.ready"

    try:
        _wait_for_file(ready_path)
        status = manager.poll_live_gui_session(launched.session_id)
        assert status.status == "running"
        assert status.bridge_pid is not None
        assert status.live_process_attached is True
        assert launched.manifest_path.is_file() is True
        assert _normalize_path_string(launched.bridge_command[0]) == _normalize_path_string(
            sys.executable
        )
        assert _normalize_path_string(launched.bridge_command[1]) == _normalize_path_string(
            str(bridge_script)
        )
        assert launched.bridge_command[-1] == str(launched.manifest_path)
        assert ready_path.read_text(encoding="utf-8") == "buck-debug"
    finally:
        closure = manager.close_live_gui_session(launched.session_id, delete_manifest=True)

    assert closure.status == "closed"
    assert closure.bridge_terminated is True
    assert closure.manifest_deleted is True
    assert launched.manifest_path.exists() is False


def test_live_gui_manager_rehydrates_completed_bridge_after_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    bridge_script = _write_bridge_script(tmp_path / "bridge_once.py", exit_immediately=True)

    first_manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )

    launched = first_manager.launch_live_gui_session(
        session_name="buck-debug",
        schematic_path=str(schematic),
    )
    terminal_status = _wait_for_terminal_status(first_manager, launched.session_id)
    assert terminal_status.status == "completed"

    second_manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )

    reloaded = second_manager.poll_live_gui_session(launched.session_id)

    assert reloaded.status == "completed"
    assert reloaded.live_process_attached is False
    assert reloaded.completed_at is not None


def test_live_gui_manager_dispatches_commands_and_reads_bridge_events(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    bridge_script = _write_bridge_script(tmp_path / "bridge_events.py", exit_immediately=False)

    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )

    launched = manager.launch_live_gui_session(
        session_name="buck-debug",
        schematic_path=str(schematic),
        waveform_names=["V(out)"],
        cross_probe_signals=["V(out)"],
    )

    try:
        _wait_for_file(launched.output_root / "bridge.ready")
        command = manager.send_live_gui_session_command(
            launched.session_id,
            command="cross_probe_signal",
            signal="V(out)",
            payload={"waveform": "V(out)", "cursor": "main"},
        )
        events = _wait_for_live_gui_events(manager, launched.session_id)
    finally:
        manager.close_live_gui_session(launched.session_id, delete_manifest=True)

    queued_lines = [
        json.loads(line)
        for line in command.command_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert command.command_id == 1
    assert command.command == "cross_probe_signal"
    assert command.signal == "V(out)"
    assert queued_lines[0]["payload"]["waveform"] == "V(out)"
    assert events.next_sequence == 1
    assert len(events.events) == 1
    assert events.events[0].event == "command_ack"
    assert events.events[0].signal == "V(out)"
    assert events.events[0].payload["waveform"] == "V(out)"


def test_run_simulation_in_session_completes_via_bridge(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    bridge_script = _write_bridge_script(tmp_path / "bridge_run.py", exit_immediately=False)

    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )
    launched = manager.launch_live_gui_session(
        session_name="buck-debug", schematic_path=str(schematic)
    )

    netlist = tmp_path / "demo.net"
    netlist.write_text("* netlist\n", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    raw_path = tmp_path / "demo.qraw"
    try:
        _wait_for_file(launched.output_root / "bridge.ready")
        reusable = manager.find_reusable_session(schematic_path=str(schematic))
        assert reusable == launched.session_id

        run = manager.run_simulation_in_session(
            launched.session_id,
            netlist_path=netlist,
            log_path=log_path,
            raw_path=raw_path,
            timeout_s=5.0,
        )
    finally:
        manager.close_live_gui_session(launched.session_id, delete_manifest=True)

    assert run.status == "completed"
    assert run.command_id >= 1
    assert log_path.read_text(encoding="utf-8") == "ok"
    assert raw_path.read_text(encoding="utf-8") == "ok"


def test_run_simulation_in_session_times_out_without_bridge_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    # A bridge that exits immediately never emits a run_netlist_complete event.
    bridge_script = _write_bridge_script(tmp_path / "bridge_idle.py", exit_immediately=True)

    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            live_gui_bridge_command=(sys.executable, str(bridge_script)),
        )
    )
    launched = manager.launch_live_gui_session(session_name="idle")
    _wait_for_terminal_status(manager, launched.session_id)

    # Force the session record back to running so the command can be queued.
    session = manager._require_session(launched.session_id)
    session.status = "running"

    netlist = tmp_path / "demo.net"
    netlist.write_text("* netlist\n", encoding="utf-8")
    run = manager.run_simulation_in_session(
        launched.session_id,
        netlist_path=netlist,
        log_path=tmp_path / "demo.log",
        raw_path=tmp_path / "demo.qraw",
        timeout_s=0.2,
    )
    assert run.status == "timeout"


def test_find_reusable_session_returns_none_without_running_sessions(
    tmp_path: Path,
) -> None:
    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    assert manager.find_reusable_session() is None


def test_live_gui_manager_requires_configured_bridge_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    manager = live_gui_manager_service.LiveGuiSessionManager(
        QSpiceSettings(workspace_root=tmp_path)
    )

    with pytest.raises(BackendUnavailableError, match="live GUI bridge command"):
        manager.launch_live_gui_session(session_name="buck-debug")
