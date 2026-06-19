"""Tests for simulation log progress polling."""

from __future__ import annotations

import sys
import threading
import time
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.infra import simulation_subprocess
from qspice_mcp.infra.simulation_subprocess import (
    _poll_log_progress,
    run_subprocess_with_log_progress,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_poll_log_progress_reports_percent_updates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "run.log"
    log_path.write_text("Time domain  25% complete\n", encoding="utf-8")
    recorded_progress: list[tuple[float, float | None, str | None]] = []
    recorded_info: list[str] = []

    def capture_progress(
        progress: float,
        *,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        recorded_progress.append((progress, total, message))

    def capture_info(message: str) -> None:
        recorded_info.append(message)

    monkeypatch.setattr(simulation_subprocess, "report_progress", capture_progress)
    monkeypatch.setattr(simulation_subprocess, "report_info", capture_info)

    stop_event = threading.Event()
    poller = threading.Thread(
        target=_poll_log_progress,
        args=(log_path, stop_event),
        name="test-log-progress",
        daemon=True,
    )
    poller.start()
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not recorded_progress:
            time.sleep(0.05)
    finally:
        stop_event.set()
        poller.join(timeout=2.0)

    assert recorded_progress
    assert recorded_progress[-1][0] == pytest.approx(25.0)
    assert recorded_info == [recorded_progress[-1][2]]


def test_poll_log_progress_skips_duplicate_percentages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_path = tmp_path / "run.log"
    log_path.write_text(
        "Time domain  50% complete\nTime domain  40% complete\nTime domain 100% done\n",
        encoding="utf-8",
    )
    recorded_progress: list[float] = []

    def capture_progress(progress: float, **kwargs: object) -> None:
        del kwargs
        recorded_progress.append(progress)

    def noop_info(message: str) -> None:
        del message

    monkeypatch.setattr(simulation_subprocess, "report_progress", capture_progress)
    monkeypatch.setattr(simulation_subprocess, "report_info", noop_info)

    stop_event = threading.Event()
    poller = threading.Thread(
        target=_poll_log_progress,
        args=(log_path, stop_event),
        name="test-log-progress-dedupe",
        daemon=True,
    )
    poller.start()
    try:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and len(recorded_progress) < 2:
            time.sleep(0.05)
    finally:
        stop_event.set()
        poller.join(timeout=2.0)

    assert recorded_progress == [pytest.approx(50.0), pytest.approx(100.0)]


def test_run_subprocess_with_log_progress_runs_command(tmp_path: Path) -> None:
    log_path = tmp_path / "run.log"
    log_path.write_text("", encoding="utf-8")

    if sys.platform == "win32":
        command = ("python", "-c", "print('done')")
    else:
        command = ("python3", "-c", "print('done')")

    result = run_subprocess_with_log_progress(
        command,
        cwd=tmp_path,
        log_path=log_path,
        timeout_s=10.0,
    )

    assert result.exit_code == 0


def test_run_subprocess_with_log_progress_without_log_path(tmp_path: Path) -> None:
    if sys.platform == "win32":
        command = ("python", "-c", "print('done')")
    else:
        command = ("python3", "-c", "print('done')")

    result = run_subprocess_with_log_progress(
        command,
        cwd=tmp_path,
        log_path=None,
        timeout_s=10.0,
    )

    assert result.exit_code == 0
