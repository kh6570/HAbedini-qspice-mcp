"""Tests for the cancel_run service."""

from __future__ import annotations

import subprocess
import sys

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra import child_processes
from qspice_mcp.services.simulation.cancel_run import cancel_run


def test_cancel_run_terminates_tracked_process() -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_processes.register_run("svc-run", process)
    try:
        result = cancel_run("svc-run")
        assert result.run_id == "svc-run"
        assert result.cancelled is True
        assert process.poll() is not None
    finally:
        child_processes.consume_run_cancellation("svc-run")
        child_processes.unregister_run("svc-run")


def test_cancel_run_unknown_run_raises() -> None:
    with pytest.raises(ValidationError):
        cancel_run("does-not-exist")


def test_cancel_run_blank_run_id_raises() -> None:
    with pytest.raises(ValidationError):
        cancel_run("   ")
