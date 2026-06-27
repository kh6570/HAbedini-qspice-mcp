"""Windows Job Object kill-on-close support for simulator child processes.

When the server process dies for any reason -- including a hard kill from the IDE
that bypasses ``atexit``/signal handlers -- Windows closes the last handle to the
job object, and the kernel terminates every process still assigned to it. This is
the only mechanism that guarantees orphan reaping on an un-catchable hard kill.

On non-Windows platforms every function here is a no-op; the cross-platform
fallback is the detached watchdog route (see ``qspice_mcp.infra.watchdog``).
"""

from __future__ import annotations

import sys
import threading

import structlog

_logger = structlog.get_logger(__name__)

_LOCK = threading.Lock()
# Opaque handle kept open for the lifetime of the process. Typed as ``object``
# so no Windows-only types leak into the cross-platform module surface.
_JOB_HANDLE: object | None = None
_JOB_UNAVAILABLE = False

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100


def _create_job_handle() -> object | None:
    """Create a kill-on-close job object, or return ``None`` when unavailable."""

    if sys.platform != "win32":
        return None

    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801
        _fields_ = (
            ("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
            ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.POINTER(wintypes.ULONG)),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        )

    class _IO_COUNTERS(ctypes.Structure):  # noqa: N801
        _fields_ = (
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        )

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801
        _fields_ = (
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        )

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        _logger.warning("job_object_create_failed", error=ctypes.get_last_error())
        return None

    info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ok = kernel32.SetInformationJobObject(
        handle,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(info),
        ctypes.sizeof(info),
    )
    if not ok:
        _logger.warning("job_object_configure_failed", error=ctypes.get_last_error())
        kernel32.CloseHandle(handle)
        return None
    _logger.debug("job_object_created")
    return int(handle)


def _ensure_job_handle() -> object | None:
    global _JOB_HANDLE, _JOB_UNAVAILABLE  # noqa: PLW0603
    if _JOB_HANDLE is not None or _JOB_UNAVAILABLE:
        return _JOB_HANDLE
    with _LOCK:
        if _JOB_HANDLE is None and not _JOB_UNAVAILABLE:
            handle = _create_job_handle()
            if handle is None:
                _JOB_UNAVAILABLE = True
            else:
                _JOB_HANDLE = handle
    return _JOB_HANDLE


def assign_process_to_kill_on_close_job(pid: int) -> bool:
    """Assign one child PID to the kill-on-close job; return ``True`` on success.

    Best-effort: returns ``False`` on non-Windows hosts, when the job object could
    not be created, or when assignment fails (for example a restrictive parent job).
    """

    if sys.platform != "win32":
        return False
    handle = _ensure_job_handle()
    if handle is None:
        return False

    import ctypes  # noqa: PLC0415

    kernel32 = ctypes.windll.kernel32
    process_handle = kernel32.OpenProcess(
        _PROCESS_SET_QUOTA | _PROCESS_TERMINATE,
        False,
        pid,
    )
    if not process_handle:
        _logger.debug("job_object_open_process_failed", pid=pid, error=ctypes.get_last_error())
        return False
    try:
        assigned = kernel32.AssignProcessToJobObject(handle, process_handle)
    finally:
        kernel32.CloseHandle(process_handle)
    if not assigned:
        _logger.debug("job_object_assign_failed", pid=pid, error=ctypes.get_last_error())
        return False
    return True


def reset_job_object_state_for_tests() -> None:
    """Reset the memoized job handle and availability flag (test-only)."""

    global _JOB_HANDLE, _JOB_UNAVAILABLE  # noqa: PLW0603
    with _LOCK:
        _JOB_HANDLE = None
        _JOB_UNAVAILABLE = False


__all__ = [
    "assign_process_to_kill_on_close_job",
    "reset_job_object_state_for_tests",
]
