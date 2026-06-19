"""Track and reap simulator child processes on shutdown."""

from __future__ import annotations

import atexit
import signal
import subprocess
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

_ACTIVE_LOCK = threading.Lock()
_ACTIVE_PROCESSES: dict[int, subprocess.Popen[Any]] = {}
_SHUTDOWN_HOOKS_INSTALLED = False


def register_process(process: subprocess.Popen[Any]) -> None:
    """Track one spawned child process for lifecycle cleanup."""

    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES[process.pid] = process


def unregister_process(pid: int) -> None:
    """Stop tracking one child process after it has exited."""

    with _ACTIVE_LOCK:
        _ACTIVE_PROCESSES.pop(pid, None)


def terminate_active_processes(*, reason: str = "shutdown") -> tuple[int, ...]:
    """Best-effort terminate all tracked child processes."""

    del reason
    terminated: list[int] = []
    with _ACTIVE_LOCK:
        processes = list(_ACTIVE_PROCESSES.items())
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
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
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
        del signum, _frame
        terminate_active_processes()
        if on_shutdown is not None:
            on_shutdown()

    atexit.register(_handle_shutdown)
    for signum in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if signum is None:
            continue
        try:
            signal.signal(signum, _handle_shutdown)
        except (OSError, ValueError):
            continue


__all__ = [
    "install_shutdown_hooks",
    "register_process",
    "terminate_active_processes",
    "unregister_process",
]
