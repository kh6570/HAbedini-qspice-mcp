"""Tests for the cross-platform orphan watchdog."""

from __future__ import annotations

import os
import subprocess
import sys

from qspice_mcp.infra import watchdog


def _spawn_sleeper(seconds: float) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [sys.executable, "-c", f"import time; time.sleep({seconds})"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_is_process_alive_true_for_current_process() -> None:
    assert watchdog.is_process_alive(os.getpid()) is True


def test_is_process_alive_false_for_nonpositive_pid() -> None:
    assert watchdog.is_process_alive(0) is False
    assert watchdog.is_process_alive(-5) is False


def test_is_process_alive_false_for_exited_process() -> None:
    process = _spawn_sleeper(0)
    process.wait(timeout=5.0)
    assert watchdog.is_process_alive(process.pid) is False


def test_reap_pids_terminates_running_child() -> None:
    process = _spawn_sleeper(30)
    reaped = watchdog.reap_pids((process.pid,), grace_s=2.0)
    assert process.pid in reaped
    process.wait(timeout=5.0)
    assert process.poll() is not None


def test_reap_pids_ignores_dead_pids() -> None:
    process = _spawn_sleeper(0)
    process.wait(timeout=5.0)
    assert watchdog.reap_pids((process.pid,)) == ()


def test_run_watchdog_reaps_children_after_parent_exits() -> None:
    parent = _spawn_sleeper(0.4)
    child = _spawn_sleeper(30)
    try:
        reaped = watchdog.run_watchdog(
            parent_pid=parent.pid,
            child_pids=(child.pid,),
            poll_interval_s=0.05,
            grace_s=2.0,
        )
        assert child.pid in reaped
        child.wait(timeout=5.0)
        assert child.poll() is not None
    finally:
        for process in (parent, child):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5.0)
