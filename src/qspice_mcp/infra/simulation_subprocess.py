"""Subprocess helpers that surface QSpice log progress to MCP clients."""

from __future__ import annotations

import queue
import re
import subprocess
import threading
import time
from typing import TYPE_CHECKING

from qspice_mcp.infra.child_processes import (
    register_process,
    register_run,
    unregister_process,
    unregister_run,
)
from qspice_mcp.infra.progress import report_info, report_progress
from qspice_mcp.infra.subprocess import SubprocessResult

if TYPE_CHECKING:
    from pathlib import Path

_PROGRESS_LINE = re.compile(
    r"(\d+(?:\.\d+)?)\s*%\s*(?:complete|done)",
    re.IGNORECASE,
)
_POLL_INTERVAL_S = 0.5


def _poll_log_progress(
    log_path: Path,
    stop_event: threading.Event,
    events: queue.Queue[tuple[float, str]],
) -> None:
    last_percent: float | None = None
    last_size = 0
    while not stop_event.is_set():
        if not log_path.is_file():
            time.sleep(_POLL_INTERVAL_S)
            continue
        try:
            current_size = log_path.stat().st_size
            if current_size < last_size:
                last_size = 0
            if current_size == last_size:
                time.sleep(_POLL_INTERVAL_S)
                continue
            payload = log_path.read_bytes()[last_size:current_size]
            last_size = current_size
            text = payload.decode("utf-8", errors="replace")
        except OSError:
            time.sleep(_POLL_INTERVAL_S)
            continue

        for line in text.splitlines():
            match = _PROGRESS_LINE.search(line)
            if match is None:
                continue
            percent = float(match.group(1))
            if last_percent is not None and percent <= last_percent:
                continue
            last_percent = percent
            events.put((percent, line.strip()))
        time.sleep(_POLL_INTERVAL_S)


def _drain_progress(events: queue.Queue[tuple[float, str]]) -> None:
    """Report queued log progress on the calling thread.

    The caller is the AnyIO worker for long-running tools, where
    ``report_progress`` can reach the client. A plain poller thread cannot.
    """

    while True:
        try:
            percent, message = events.get_nowait()
        except queue.Empty:
            return
        report_progress(percent, total=100.0, message=message)
        report_info(message)


def run_subprocess_with_log_progress(
    command: tuple[str, ...],
    *,
    cwd: Path,
    log_path: Path | None,
    timeout_s: float | None = None,
    env: dict[str, str] | None = None,
    run_id: str | None = None,
) -> SubprocessResult:
    """Run QSpice and poll the simulation log for phase progress notifications."""

    started_at = time.perf_counter()
    process = subprocess.Popen(  # noqa: S603
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        env=env,
    )
    register_process(process)
    if run_id is not None:
        register_run(run_id, process)
    stop_event = threading.Event()
    progress_events: queue.Queue[tuple[float, str]] = queue.Queue()
    poller: threading.Thread | None = None
    if log_path is not None:
        poller = threading.Thread(
            target=_poll_log_progress,
            args=(log_path, stop_event, progress_events),
            name="qspice-log-progress",
            daemon=True,
        )
        poller.start()

    def _wait_for_process() -> tuple[str, str]:
        deadline = None if timeout_s is None else time.perf_counter() + timeout_s
        while True:
            remaining = None if deadline is None else deadline - time.perf_counter()
            if remaining is not None and remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout_s or 0)
            slice_timeout = (
                _POLL_INTERVAL_S if remaining is None else min(_POLL_INTERVAL_S, remaining)
            )
            try:
                return process.communicate(timeout=slice_timeout)
            except subprocess.TimeoutExpired:
                _drain_progress(progress_events)

    try:
        stdout, stderr = _wait_for_process()
    except subprocess.TimeoutExpired as exc:
        process.kill()
        captured_stdout, captured_stderr = process.communicate()
        exc.stdout = captured_stdout  # type: ignore[assignment]
        exc.stderr = captured_stderr  # type: ignore[assignment]
        raise
    finally:
        stop_event.set()
        if poller is not None:
            poller.join(timeout=1.0)
        _drain_progress(progress_events)
        unregister_process(process.pid)
        if run_id is not None:
            unregister_run(run_id)
    return SubprocessResult(
        command=tuple(command),
        working_directory=cwd,
        exit_code=process.returncode,
        duration_s=time.perf_counter() - started_at,
        stdout=stdout or "",
        stderr=stderr or "",
    )


__all__ = ["run_subprocess_with_log_progress"]
