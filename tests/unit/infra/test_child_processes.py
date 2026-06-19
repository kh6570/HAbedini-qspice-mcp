"""Tests for child-process lifecycle tracking."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

from qspice_mcp.infra import child_processes

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_terminate_active_processes_reaps_running_child() -> None:
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_processes.register_process(process)

    terminated = child_processes.terminate_active_processes(reason="test")

    assert process.pid in terminated
    assert process.poll() is not None


def test_terminate_active_processes_unregisters_exited_child() -> None:
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "print('done')"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    process.wait(timeout=5.0)
    child_processes.register_process(process)

    terminated = child_processes.terminate_active_processes(reason="test")

    assert terminated == ()
    assert process.pid not in child_processes._ACTIVE_PROCESSES  # noqa: SLF001


def test_unregister_process_removes_tracked_pid() -> None:
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", "print('done')"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    process.wait(timeout=5.0)
    child_processes.register_process(process)
    child_processes.unregister_process(process.pid)

    terminated = child_processes.terminate_active_processes(reason="test")

    assert process.pid not in terminated


def test_install_shutdown_hooks_is_idempotent(monkeypatch: MonkeyPatch) -> None:
    child_processes._SHUTDOWN_HOOKS_INSTALLED = False  # noqa: SLF001
    registrations: list[object] = []
    monkeypatch.setattr(child_processes.atexit, "register", registrations.append)
    monkeypatch.setattr(child_processes.signal, "signal", lambda *_args, **_kwargs: None)

    child_processes.install_shutdown_hooks(on_shutdown=lambda: None)
    child_processes.install_shutdown_hooks(on_shutdown=lambda: None)

    assert len(registrations) == 1


def test_install_shutdown_hooks_invokes_callback(monkeypatch: MonkeyPatch) -> None:
    child_processes._SHUTDOWN_HOOKS_INSTALLED = False  # noqa: SLF001
    handlers: list[object] = []
    monkeypatch.setattr(child_processes.atexit, "register", handlers.append)
    monkeypatch.setattr(child_processes.signal, "signal", lambda *_args, **_kwargs: None)
    calls: list[str] = []

    child_processes.install_shutdown_hooks(on_shutdown=lambda: calls.append("shutdown"))
    handler = handlers[0]
    assert callable(handler)
    handler()

    assert calls == ["shutdown"]
