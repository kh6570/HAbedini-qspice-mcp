# In the name of God, the Most Gracious, the Most Merciful
"""Tests for remembering and stopping only PIDs this server spawned."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

from qspice_mcp.infra import spawned_processes
from qspice_mcp.infra.spawned_processes import (
    clear_spawned_pids,
    forget_spawned_pid,
    image_pids,
    remember_new_image_pids,
    remember_qspice_process,
    remember_spawned_pid,
    spawned_pids,
    terminate_spawned_processes,
)


@pytest.fixture(autouse=True)
def _clear_pids():
    clear_spawned_pids()
    yield
    clear_spawned_pids()


def test_remember_ignores_non_positive_and_non_qspice_commands() -> None:
    remember_spawned_pid(0)
    remember_spawned_pid(-4)
    remember_qspice_process((), 12)
    remember_qspice_process(("notepad.exe",), 12)
    forget_spawned_pid(99)

    assert spawned_pids() == ()


def test_remember_qspice_executable_and_new_image_pids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        spawned_processes,
        "image_pids",
        lambda image_name: {10, 12} if image_name == "QSPICE64.exe" else set(),
    )

    remember_qspice_process((r"C:\Program Files\QSPICE\QSPICE64.exe", "demo.qsch"), 8)
    fresh = remember_new_image_pids("QSPICE64.exe", {10})

    assert fresh == (12,)
    assert spawned_pids() == (8, 12)


def test_image_pids_parses_tasklist_and_skips_other_platforms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        assert command[0] == "tasklist"
        return SimpleNamespace(
            stdout="\n".join(
                (
                    '"QSPICE64.exe","4321","Console","1","100 K"',
                    "INFO: No tasks are running which match the specified criteria.",
                    '"QSPICE64.exe","nope"',
                )
            )
        )

    monkeypatch.setattr(spawned_processes, "_is_windows", lambda: True)
    monkeypatch.setattr(spawned_processes.subprocess, "run", fake_run)

    assert image_pids("  ") == set()
    assert image_pids("QSPICE64.exe") == {4321}

    monkeypatch.setattr(spawned_processes, "_is_windows", lambda: False)
    assert image_pids("QSPICE64.exe") == set()


def test_terminate_returns_none_when_nothing_was_spawned() -> None:
    assert terminate_spawned_processes() == ((), None)


def test_terminate_stops_a_process_this_server_started() -> None:
    process = subprocess.Popen(
        (sys.executable, "-c", "import time; time.sleep(30)"),
    )
    remember_spawned_pid(process.pid)

    killed, code = terminate_spawned_processes()
    process.wait(timeout=5)

    assert killed == (process.pid,)
    assert code == 0
    assert spawned_pids() == ()
    assert process.returncode is not None


def test_terminate_reports_failure_when_no_pid_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    remember_spawned_pid(2_000_000_001)
    monkeypatch.setattr(spawned_processes, "_kill_pid", lambda _pid: 128)

    assert terminate_spawned_processes() == ((), 128)
    assert spawned_pids() == ()


def test_kill_pid_uses_taskkill_or_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(spawned_processes, "_is_windows", lambda: True)
    monkeypatch.setattr(spawned_processes.subprocess, "run", fake_run)
    remember_spawned_pid(77)
    assert terminate_spawned_processes() == ((77,), 0)
    assert commands[0][:3] == ["taskkill", "/F", "/PID"]

    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(spawned_processes, "_is_windows", lambda: False)
    monkeypatch.setattr(spawned_processes.os, "kill", lambda pid, sig: signals.append((pid, sig)))
    remember_spawned_pid(78)
    assert terminate_spawned_processes() == ((78,), 0)
    assert signals == [(78, 15)]

    def fail_kill(_pid: int, _sig: int) -> None:
        raise OSError("gone")

    monkeypatch.setattr(spawned_processes.os, "kill", fail_kill)
    remember_spawned_pid(79)
    assert terminate_spawned_processes() == ((), 1)
