"""Track and reap simulator child processes on shutdown."""

from __future__ import annotations

import atexit
import contextlib
import signal
import subprocess
import threading
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import Callable

_ACTIVE_LOCK = threading.Lock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen[Any]] = {}
_RUN_PROCESSES: dict[str, subprocess.Popen[Any]] = {}
_CANCELLED_RUNS: set[str] = set()
_SHUTDOWN_HOOKS_INSTALLED = False
_DEFAULT_GRACE_S = 2.0

_logger = structlog.get_logger(__name__)


def register_process(process: subprocess.Popen[Any]) -> None:
    """Track one spawned child process for lifecycle cleanup."""

    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES[process.pid] = process


def unregister_process(pid: int) -> None:
    """Stop tracking one child process after it has exited."""

    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES.pop(pid, None)


def register_run(run_id: str, process: subprocess.Popen[Any]) -> None:
    """Associate one caller-supplied run id with its live child process."""

    with _ACTIVE_LOCK:
        _RUN_PROCESSES[run_id] = process
        _CANCELLED_RUNS.discard(run_id)


def unregister_run(run_id: str) -> None:
    """Stop tracking one run id's process while preserving any cancellation flag."""

    with _ACTIVE_LOCK:
        _RUN_PROCESSES.pop(run_id, None)


def is_run_cancelled(run_id: str) -> bool:
    """Return whether one run id has been marked for cancellation."""

    with _ACTIVE_LOCK:
        return run_id in _CANCELLED_RUNS


def consume_run_cancellation(run_id: str) -> bool:
    """Return and clear the cancellation flag for one run id."""

    with _ACTIVE_LOCK:
        if run_id in _CANCELLED_RUNS:
            _CANCELLED_RUNS.discard(run_id)
            return True
        return False


def request_run_cancellation(run_id: str, *, grace_s: float = _DEFAULT_GRACE_S) -> bool:
    """Terminate the live process for one run id; return False when it is unknown."""

    with _ACTIVE_LOCK:
        process = _RUN_PROCESSES.get(run_id)
        if process is None:
            return False
        _CANCELLED_RUNS.add(run_id)

    if process.poll() is not None:
        return True
    _logger.info("simulation_run_cancellation_requested", run_id=run_id, pid=process.pid)
    with contextlib.suppress(OSError):
        process.terminate()
    try:
        process.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            process.kill()
    return True


def terminate_active_processes(
    *,
    reason: str = "shutdown",
    grace_s: float = _DEFAULT_GRACE_S,
) -> tuple[int, ...]:
    """Best-effort terminate all tracked child processes within a grace window."""

    terminated: list[int] = []
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES.items())
    if processes:
        _logger.info(
            "terminating_active_processes",
            reason=reason,
            pids=[pid for pid, _ in processes],
            grace_s=grace_s,
        )
    for pid, process in processes:
        if process.poll() is not None:
            unregister_process(pid)
            continue
        try:
            process.terminate()
            terminated.append(pid)
        except OSError:
            unregister_process(pid)
    for pid, process in processes:
        if pid not in terminated:
            continue
        try:
            process.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            _logger.warning("force_killing_child_process", reason=reason, pid=pid)
            with contextlib.suppress(OSError):
                process.kill()
        finally:
            unregister_process(pid)
    return tuple(terminated)


def install_shutdown_hooks(*, on_shutdown: Callable[[], None] | None = None) -> None:
    """Register atexit and signal handlers once per process."""

    global _SHUTDOWN_HOOKS_INSTALLED  # noqa: PLW0603
    if _SHUTDOWN_HOOKS_INSTALLED:
        return
    _SHUTDOWN_HOOKS_INSTALLED = True

    def _handle_shutdown(signum: int | None = None, _frame: object | None = None) -> None:
        reason = "signal" if signum is not None else "atexit"
        if on_shutdown is not None:
            with contextlib.suppress(Exception):
                on_shutdown()
        terminate_active_processes(reason=reason)

    atexit.register(_handle_shutdown)
    for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if signum is None:
            continue
        try:
            signal.signal(signum, _handle_shutdown)
        except (OSError, ValueError):
            continue


__all__ = [
    "consume_run_cancellation",
    "install_shutdown_hooks",
    "is_run_cancelled",
    "register_process",
    "register_run",
    "request_run_cancellation",
    "terminate_active_processes",
    "unregister_process",
    "unregister_run",
]
