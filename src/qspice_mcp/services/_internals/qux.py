"""Helpers for QUX companion-executable discovery and invocation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.adapters.probe import ProbeResult, probe_qspice
from qspice_mcp.core.exceptions import (
    BackendUnavailableError,
    QSpiceError,
    SimulationTimeoutError,
    ValidationError,
)
from qspice_mcp.infra.subprocess import SubprocessResult, run_subprocess

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

QuxExportFormat = Literal["csv", "ascii", "spice", "s2p"]

COMPANION_NAME = "QUX.exe"
SUPPORTED_EXPORT_FORMATS: tuple[QuxExportFormat, ...] = ("csv", "ascii", "spice", "s2p")
SUPPORTED_SWITCHES: tuple[str, ...] = ("-Export", "-Netlist", "-DLLvariables")
WAVEFORM_INPUT_SUFFIXES: tuple[str, ...] = (".qraw",)
SCHEMATIC_INPUT_SUFFIXES: tuple[str, ...] = (".qsch",)
_MIN_EXPORT_POINT_COUNT = 2


def _normalize_export_expressions(expressions: tuple[str, ...]) -> tuple[str, ...]:
    """Reject empty or switch-like expressions before invoking QUX."""

    normalized: list[str] = []
    for expression in expressions:
        token = expression.strip()
        if not token:
            continue
        if token.startswith("-"):
            raise ValidationError(
                "Export expressions cannot start with '-' because QUX would interpret them "
                "as switches."
            )
        normalized.append(token)
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class QuxCompanion:
    """Resolved QUX companion executable metadata."""

    qspice_executable: Path
    qux_path: Path
    probe: ProbeResult


def resolve_qux_companion(settings: QSpiceSettings) -> QuxCompanion:
    """Resolve `QUX.exe` next to the configured or discovered QSpice executable."""

    effective_settings = settings.normalized()
    probe = probe_qspice(effective_settings)
    if probe.executable is None or not probe.exists:
        raise BackendUnavailableError("QSpice executable is required to resolve QUX.exe")

    qux_path = probe.executable.with_name(COMPANION_NAME)
    if not qux_path.is_file():
        raise BackendUnavailableError(
            f"QUX.exe was not found next to the configured QSpice executable: {qux_path}"
        )

    return QuxCompanion(
        qspice_executable=probe.executable.resolve(strict=False),
        qux_path=qux_path.resolve(strict=False),
        probe=probe,
    )


def build_qux_export_command(
    qux_path: Path,
    raw_path: Path,
    *,
    expressions: tuple[str, ...],
    export_format: QuxExportFormat,
    point_count: int | None = None,
    stdout: bool = False,
) -> tuple[str, ...]:
    """Build a `QUX.exe -Export` command line."""

    normalized_expressions = _normalize_export_expressions(expressions)
    if not normalized_expressions:
        raise ValidationError("At least one export expression is required.")
    if point_count is not None and point_count < _MIN_EXPORT_POINT_COUNT:
        raise ValidationError("point_count must be at least 2 when provided.")

    command: list[str] = [str(qux_path), "-Export", str(raw_path), *normalized_expressions]
    if point_count is not None:
        command.append(str(point_count))
    command.append(export_format.upper())
    if stdout:
        command.append("-stdout")
    return tuple(command)


def build_dll_variables_command(
    qux_path: Path,
    schematic_path: Path,
    *,
    stdout: bool = False,
) -> tuple[str, ...]:
    """Build a `QUX.exe -DLLvariables` command line."""

    command: list[str] = [str(qux_path), "-DLLvariables", str(schematic_path)]
    if stdout:
        command.append("-stdout")
    return tuple(command)


def build_qux_netlist_command(qux_path: Path, schematic_path: Path) -> tuple[str, ...]:
    """Build a `QUX.exe -Netlist` command line."""

    return (str(qux_path), "-Netlist", str(schematic_path))


def discover_qux_netlist_output(schematic_path: Path) -> Path | None:
    """Return a sibling derived netlist artifact produced by QUX `-Netlist`."""

    for suffix in (".cir", ".net"):
        candidate = schematic_path.with_suffix(suffix)
        if candidate.is_file():
            return candidate.resolve(strict=False)
    return None


def run_qux_command(
    command: tuple[str, ...],
    *,
    cwd: Path,
    timeout_s: float | None = None,
) -> SubprocessResult:
    """Run a QUX companion command and raise a domain error on failure."""

    try:
        result = run_subprocess(command, cwd=cwd, timeout_s=timeout_s)
    except subprocess.TimeoutExpired as exc:
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else exc.stderr
        )
        raise SimulationTimeoutError(
            "QUX companion command timed out.",
            stderr=stderr,
        ) from exc
    if result.exit_code != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostics available"
        raise QSpiceError(f"QUX companion command failed: {detail}")
    return result


__all__ = [
    "COMPANION_NAME",
    "SCHEMATIC_INPUT_SUFFIXES",
    "SUPPORTED_EXPORT_FORMATS",
    "SUPPORTED_SWITCHES",
    "WAVEFORM_INPUT_SUFFIXES",
    "QuxCompanion",
    "QuxExportFormat",
    "build_dll_variables_command",
    "build_qux_export_command",
    "build_qux_netlist_command",
    "discover_qux_netlist_output",
    "resolve_qux_companion",
    "run_qux_command",
]
