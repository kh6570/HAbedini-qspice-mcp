# In the name of God, the Most Gracious, the Most Merciful
"""PIDs this server spawned, so a GUI restart does not kill every QSpice."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import PureWindowsPath

_LOCK = threading.Lock()
_PIDS: set[int] = set()
_TASKLIST_PID_INDEX = 1
_MIN_TASKLIST_COLUMNS = 2


def remember_spawned_pid(pid: int) -> None:
    """Remember one process this server started."""

    if pid <= 0:
        return
    with _LOCK:
        _PIDS.add(pid)


def forget_spawned_pid(pid: int) -> None:
    """Drop one PID after the process has exited or been stopped."""

    with _LOCK:
        _PIDS.discard(pid)


def spawned_pids() -> tuple[int, ...]:
    """Return remembered PIDs in ascending order."""

    with _LOCK:
        return tuple(sorted(_PIDS))


def clear_spawned_pids() -> None:
    """Forget every remembered PID. Tests use this between cases."""

    with _LOCK:
        _PIDS.clear()


def _is_windows() -> bool:
    return os.name == "nt"


def _executable_name(command: str) -> str:
    """Return the image name, including when the command uses Windows separators."""

    return PureWindowsPath(command).name


def remember_qspice_process(command: tuple[str, ...], pid: int) -> None:
    """Remember a PID when the command starts a QSpice executable."""

    if not command:
        return
    if _executable_name(command[0]).casefold().startswith("qspice"):
        remember_spawned_pid(pid)


def image_pids(image_name: str) -> set[int]:
    """Return PIDs whose image name matches, on Windows."""

    if not _is_windows() or not image_name.strip():
        return set()
    completed = subprocess.run(  # noqa: S603
        ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    found: set[int] = set()
    for line in completed.stdout.splitlines():
        parts = [part.strip().strip('"') for part in line.split(",")]
        if len(parts) >= _MIN_TASKLIST_COLUMNS and parts[_TASKLIST_PID_INDEX].isdigit():
            found.add(int(parts[_TASKLIST_PID_INDEX]))
    return found


def remember_new_image_pids(image_name: str, before: set[int]) -> tuple[int, ...]:
    """Remember QSpice PIDs that appeared after this server launched a GUI file."""

    fresh = tuple(sorted(image_pids(image_name) - before))
    for pid in fresh:
        remember_spawned_pid(pid)
    return fresh


def _kill_pid(pid: int) -> int:
    if _is_windows():
        completed = subprocess.run(  # noqa: S603
            ["taskkill", "/F", "/PID", str(pid)],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
        return int(completed.returncode)
    try:
        os.kill(pid, 15)
    except OSError:
        return 1
    return 0


def terminate_spawned_processes() -> tuple[tuple[int, ...], int | None]:
    """Stop remembered PIDs.

    The first item is the PIDs that taskkill reported as stopped. The exit
    code is ``None`` when this server had no spawned PID to stop, and ``0``
    when at least one stop succeeded.
    """

    pids = spawned_pids()
    if not pids:
        return (), None
    killed: list[int] = []
    failure: int | None = None
    for pid in pids:
        code = _kill_pid(pid)
        forget_spawned_pid(pid)
        if code == 0:
            killed.append(pid)
            continue
        if failure is None:
            failure = code
    if killed:
        return tuple(killed), 0
    return (), failure


__all__ = [
    "clear_spawned_pids",
    "forget_spawned_pid",
    "image_pids",
    "remember_new_image_pids",
    "remember_qspice_process",
    "remember_spawned_pid",
    "spawned_pids",
    "terminate_spawned_processes",
]
