"""Capability probing for the QSpice executable."""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Literal

from qspice_mcp.infra.config import QSpiceSettings

ProbeSource = Literal["configured", "default-location", "path", "unavailable"]
VersionSource = Literal["cli", "metadata", "timestamp", "unavailable"]


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """Summary of the discovered QSpice executable state."""

    configured: bool
    executable: Path | None
    exists: bool
    source: ProbeSource
    version: str | None = None
    version_source: VersionSource = "unavailable"
    note: str = ""


def default_install_locations() -> tuple[Path, ...]:
    """Return the default Windows install locations worth probing."""

    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    return (
        Path.home() / "AppData" / "Local" / "Programs" / "Qspice" / "QSPICE64.exe",
        program_files / "QSPICE" / "QSPICE64.exe",
    )


def discover_executable(configured_executable: Path | None) -> tuple[Path | None, ProbeSource]:
    """Return the configured executable or the first discovered fallback."""

    if configured_executable is not None:
        return configured_executable.resolve(strict=False), "configured"

    for candidate in default_install_locations():
        if candidate.is_file():
            return candidate.resolve(strict=False), "default-location"

    for candidate_name in ("QSPICE64.exe", "QSPICE64", "QSPICE.exe", "QSPICE"):
        discovered_path: str | None = which(candidate_name)
        if discovered_path is not None:
            return Path(discovered_path).resolve(strict=False), "path"

    return None, "unavailable"


# ---------------------------------------------------------------------------
# Version detection strategies
# ---------------------------------------------------------------------------

_VERSION_LINE_PATTERN = re.compile(
    r"(?:version|v\.?|release)\s*[:=]?\s*(\d+(?:\.\d+){1,3})",
    re.IGNORECASE,
)
_CLI_PROBE_TIMEOUT_S = 2.0
_CLI_PROBE_FLAGS = ("--version", "-v")


def _cli_probe_timeout_s() -> float:
    """Return the CLI probe timeout, optionally overridden by environment."""

    raw = os.environ.get("QSPICE_PROBE_CLI_TIMEOUT", "").strip()
    if not raw:
        return _CLI_PROBE_TIMEOUT_S
    try:
        return max(0.5, float(raw))
    except ValueError:
        return _CLI_PROBE_TIMEOUT_S


def _skip_cli_probe() -> bool:
    """Return whether CLI probing should be skipped for faster startup."""

    return os.environ.get("QSPICE_PROBE_SKIP_CLI", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _detect_version_cli(executable: Path) -> tuple[str | None, VersionSource]:
    """Try common version-reporting CLI flags and parse response text."""

    for flag in _CLI_PROBE_FLAGS:
        try:
            result = subprocess.run(  # noqa: S603
                [str(executable), flag],
                capture_output=True,
                text=True,
                timeout=_cli_probe_timeout_s(),
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        output = (result.stdout or result.stderr or "").strip()
        if not output:
            continue
        first_line = output.splitlines()[0].strip()
        match = _VERSION_LINE_PATTERN.search(first_line)
        if match:
            return match.group(1), "cli"
    return None, "unavailable"


def _detect_version_metadata(executable: Path) -> tuple[str | None, VersionSource]:
    """Read the PE file version resource on Windows via native API."""

    if sys.platform != "win32":
        return None, "unavailable"
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        version_dll = ctypes.WinDLL("version", use_last_error=True)
        path = str(executable)

        size = kernel32.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None, "unavailable"

        buf = ctypes.create_string_buffer(size)
        if not kernel32.GetFileVersionInfoW(path, 0, size, buf):
            return None, "unavailable"

        fixed_info_ptr = ctypes.c_void_p()
        fixed_info_len = wintypes.UINT()
        if version_dll.VerQueryValueW(
            buf, ctypes.c_wchar_p("\\"), ctypes.byref(fixed_info_ptr), ctypes.byref(fixed_info_len)
        ):
            info = ctypes.cast(fixed_info_ptr, ctypes.POINTER(ctypes.c_uint32 * 13))[0]
            ms = (info[2], info[3])  # dwFileVersionMS, dwFileVersionLS
            return f"{ms[0] >> 16}.{ms[0] & 0xFFFF}.{ms[1] >> 16}.{ms[1] & 0xFFFF}", "metadata"
    except Exception:
        return None, "unavailable"
    return None, "unavailable"


def _detect_version_timestamp(executable: Path) -> tuple[str, VersionSource]:
    """Use file modification date as a fallback version indicator."""

    mtime = executable.stat().st_mtime
    return datetime.fromtimestamp(mtime).strftime("%Y%m%d"), "timestamp"


def _detect_executable_version(executable: Path) -> tuple[str | None, VersionSource]:
    """Detect the executable version using the fastest reliable strategy first."""

    if sys.platform == "win32":
        version, source = _detect_version_metadata(executable)
        if version is not None:
            return version, source

    if not _skip_cli_probe():
        version, source = _detect_version_cli(executable)
        if version is not None:
            return version, source

    if sys.platform != "win32":
        version, source = _detect_version_metadata(executable)
        if version is not None:
            return version, source

    return _detect_version_timestamp(executable)


# ---------------------------------------------------------------------------
# Public probe entry points
# ---------------------------------------------------------------------------


def probe_qspice(settings: QSpiceSettings | None = None) -> ProbeResult:
    """Inspect the configured or discoverable QSpice executable."""

    effective_settings = (
        settings.normalized() if settings is not None else QSpiceSettings().normalized()
    )
    executable, source = discover_executable(effective_settings.exe)

    version: str | None = None
    version_source: VersionSource = "unavailable"
    note_parts: list[str] = []

    if executable is not None and executable.is_file():
        version, version_source = _detect_executable_version(executable)

        if version is not None:
            note_parts.append(f"Detected version: {version} (source: {version_source})")
        if version_source == "timestamp":
            note_parts.append(
                "Version derived from file modification date; --version flag "
                "and PE metadata were unavailable."
            )

    return ProbeResult(
        configured=effective_settings.exe is not None,
        executable=executable,
        exists=executable.is_file() if executable is not None else False,
        source=source,
        version=version,
        version_source=version_source,
        note=" | ".join(note_parts) if note_parts else "",
    )


def build_summary(settings: QSpiceSettings | None = None) -> dict[str, object]:
    """Return a JSON-serializable summary for scripts and diagnostics."""

    result = probe_qspice(settings)
    return {
        "configured": result.configured,
        "executable": str(result.executable) if result.executable is not None else None,
        "exists": result.exists,
        "source": result.source,
        "version": result.version,
        "version_source": result.version_source,
        "note": result.note,
    }
