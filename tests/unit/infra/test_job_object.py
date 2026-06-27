"""Tests for the Windows kill-on-close job object helper."""

from __future__ import annotations

import subprocess
import sys

import pytest

from qspice_mcp.infra import job_object


def test_assign_returns_false_on_non_windows() -> None:
    if sys.platform == "win32":
        pytest.skip("Windows uses a real job object; covered by the win32 tests.")
    assert job_object.assign_process_to_kill_on_close_job(999_999) is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only job object behavior.")
def test_assign_returns_bool_for_real_child_on_windows() -> None:
    job_object.reset_job_object_state_for_tests()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        result = job_object.assign_process_to_kill_on_close_job(process.pid)
        assert isinstance(result, bool)
    finally:
        process.kill()
        process.wait(timeout=5.0)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only job object behavior.")
def test_assign_returns_false_for_unknown_pid_on_windows() -> None:
    job_object.reset_job_object_state_for_tests()
    assert job_object.assign_process_to_kill_on_close_job(999_999_998) is False
