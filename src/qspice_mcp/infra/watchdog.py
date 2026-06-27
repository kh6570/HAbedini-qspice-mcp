"""Detached orphan watchdog: the cross-platform fallback to the Windows job object.

A watchdog process is seeded with a parent PID and a set of child PIDs. It polls the
parent and, once the parent is gone, reaps the children. This guarantees orphan
cleanup on platforms (or restrictive job configurations) where the kill-on-close job
object is unavailable.

All process probing avoids ``os.kill(pid, 0)`` on Windows, where that call routes
through ``TerminateProcess`` and would kill the very process it means to inspect.
"""

from __future__ import annotations

import os
import signal
import sys
import time

import structlog

_logger = structlog.get_logger(__name__)

_DEFAULT_POLL_INTERVAL_S = 1.0
_DEFAULT_GRACE_S = 2.0


def _is_alive_windows(pid: int) -> bool:
    if sys.platform != "win32":
        return False
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


def _is_alive_posix(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def is_process_alive(pid: int) -> bool:
    """Return whether a process id is currently running (platform-safe)."""

    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _is_alive_windows(pid)
    return _is_alive_posix(pid)


def _signal_process(pid: int, sig: int) -> None:
    try:
        os.kill(pid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        return


def reap_pids(pids: tuple[int, ...], *, grace_s: float = _DEFAULT_GRACE_S) -> tuple[int, ...]:
    """Terminate the given PIDs (graceful, then forceful); return reaped PIDs."""

    targets = tuple(dict.fromkeys(pid for pid in pids if pid > 0 and is_process_alive(pid)))
    if not targets:
        return ()
    for pid in targets:
        _signal_process(pid, signal.SIGTERM)
    deadline = time.monotonic() + grace_s
    while time.monotonic() < deadline and any(is_process_alive(pid) for pid in targets):
        time.sleep(0.05)
    force_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    for pid in targets:
        if is_process_alive(pid):
            _signal_process(pid, force_signal)
    _logger.info("watchdog_reaped_orphans", pids=list(targets))
    return targets


def run_watchdog(
    *,
    parent_pid: int,
    child_pids: tuple[int, ...],
    poll_interval_s: float = _DEFAULT_POLL_INTERVAL_S,
    grace_s: float = _DEFAULT_GRACE_S,
) -> tuple[int, ...]:
    """Wait for ``parent_pid`` to exit, then reap ``child_pids``.

    Returns the PIDs that were reaped. If the parent is already gone the children
    are reaped immediately.
    """

    while is_process_alive(parent_pid):
        time.sleep(poll_interval_s)
    return reap_pids(child_pids, grace_s=grace_s)


__all__ = [
    "is_process_alive",
    "reap_pids",
    "run_watchdog",
]
