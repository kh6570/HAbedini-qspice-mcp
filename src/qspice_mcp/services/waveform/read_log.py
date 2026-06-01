"""Service for QSpice log inspection and measure extraction."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.core.exceptions import (
    BackendUnavailableError,
    SimulationError,
    SimulationTimeoutError,
)
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.subprocess import run_subprocess
from qspice_mcp.services._internals.managed_outputs import (
    build_staged_output_path,
    commit_staged_output,
    discard_staged_output,
)
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_STEP_PATTERN = re.compile(r"^\s*(\d+) of \d+ steps:\s+\.step (.*)$", re.IGNORECASE)
_MEAS_PATTERN = re.compile(r"^\.meas\s+(\w+)\s+(\w+)\s+(.*)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class LogStepVariable:
    """One stepped variable and all of its values."""

    name: str
    values: tuple[str | int | float, ...]


@dataclass(frozen=True, slots=True)
class LogMeasurement:
    """One parsed measurement block from a QPOST-generated `.meas` file."""

    name: str
    analysis: str
    expression: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str | int | float, ...], ...]


@dataclass(frozen=True, slots=True)
class LogInspection:
    """Concise log summary plus optional measure extraction results."""

    log_path: Path
    line_count: int
    excerpt: str
    step_count: int
    step_variables: tuple[LogStepVariable, ...]
    measures: tuple[LogMeasurement, ...]
    meas_path: Path | None
    qpost_command: tuple[str, ...] | None
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="read_log",
    title="Read Simulation Log",
    summary="Return a concise log excerpt plus optional QPOST-derived measure data.",
    phase="implemented",
)


def _convert_value(token: str) -> str | int | float:
    """Convert a token to int or float when that is lossless enough for logs."""

    stripped = token.strip()
    if not stripped:
        return stripped
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped


def _parse_step_variables(lines: tuple[str, ...]) -> tuple[int, tuple[LogStepVariable, ...]]:
    """Extract stepped variable names and values from a QSpice log."""

    values_by_name: dict[str, list[str | int | float]] = {}
    step_count = 0
    for line in lines:
        match = _STEP_PATTERN.match(line)
        if match is None:
            continue
        step_count += 1
        for token in match.group(2).split():
            if "=" not in token:
                continue
            name, raw_value = token.split("=", 1)
            values_by_name.setdefault(name.lower(), []).append(_convert_value(raw_value))
    step_variables = tuple(
        LogStepVariable(name=name, values=tuple(values)) for name, values in values_by_name.items()
    )
    return step_count, step_variables


def _default_columns(name: str, row_width: int, *, stepped: bool) -> tuple[str, ...]:
    """Infer column names from the first row shape, mirroring the reference format."""

    if row_width <= 0:
        return ()
    if stepped:
        if row_width == 1:
            return ("step",)
        return ("step", name, *[f"{name}_{index}" for index in range(1, row_width - 1)])
    return (name, *[f"{name}_{index}" for index in range(1, row_width)])


def _parse_meas_file(meas_path: Path, *, stepped: bool) -> tuple[LogMeasurement, ...]:
    """Parse a QPOST-generated `.meas` file into structured measurement blocks."""

    measures: list[LogMeasurement] = []
    current_name: str | None = None
    current_analysis: str | None = None
    current_expression: str | None = None
    current_rows: list[tuple[str | int | float, ...]] = []

    def flush() -> None:
        nonlocal current_name, current_analysis, current_expression, current_rows
        if current_name is None or current_analysis is None or current_expression is None:
            current_rows = []
            return
        columns = _default_columns(
            current_name, len(current_rows[0]) if current_rows else 0, stepped=stepped
        )
        measures.append(
            LogMeasurement(
                name=current_name,
                analysis=current_analysis,
                expression=current_expression,
                columns=columns,
                rows=tuple(current_rows),
            )
        )
        current_name = None
        current_analysis = None
        current_expression = None
        current_rows = []

    for raw_line in meas_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _MEAS_PATTERN.match(line)
        if match is not None:
            flush()
            token1, token2, expression = match.groups()
            if token1.lower() in {"tran", "ac", "dc", "op", "noise", "tf"}:
                current_analysis = token1.lower()
                current_name = token2.lower()
            else:
                current_name = token1.lower()
                current_analysis = token2.lower()
            current_expression = expression
            continue
        if current_name is not None:
            current_rows.append(tuple(_convert_value(token) for token in line.split()))
    flush()
    return tuple(measures)


def _resolve_meas_path(
    meas_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
) -> Path:
    """Resolve an optional measure output path within the workspace."""

    if meas_path is None:
        return default.resolve(strict=False)
    return resolve_workspace_path(meas_path, workspace_root=workspace_root)


def _find_associated_netlist(log_path: Path) -> Path | None:
    """Find the sibling `.net` or `.cir` file used by QPOST."""

    for suffix in (".net", ".cir"):
        candidate = log_path.with_suffix(suffix)
        if candidate.is_file():
            return candidate.resolve(strict=False)
    return None


def _derive_qpost_path(settings: QSpiceSettings) -> Path:
    """Resolve the companion QPOST executable next to QSPICE64.exe."""

    probe = probe_qspice(settings)
    if probe.executable is None or not probe.exists:
        raise BackendUnavailableError("QSpice executable is required to derive QPOST.exe")
    qpost_path = probe.executable.with_name("QPOST.exe")
    if not qpost_path.is_file():
        raise BackendUnavailableError(
            f"QPOST.exe was not found next to the configured QSpice executable: {qpost_path}"
        )
    return qpost_path.resolve(strict=False)


def read_log(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None = None,
    max_lines: int = 80,
    include_measures: bool = True,
    refresh_measures: bool = True,
    meas_path: str | Path | None = None,
    timeout_s: float | None = None,
) -> LogInspection:
    """Read a QSpice log file and optionally materialize `.MEAS` results through QPOST."""

    normalized_workspace = workspace_root.resolve(strict=False)
    effective_settings = (
        settings.normalized()
        if settings is not None
        else QSpiceSettings(workspace_root=normalized_workspace).normalized()
    )
    log_path = validate_existing_file(
        raw_path, workspace_root=normalized_workspace, suffixes=(".log",)
    )
    lines = tuple(log_path.read_text(encoding="utf-8", errors="replace").splitlines())
    excerpt = "\n".join(lines[-max_lines:]) if max_lines > 0 else ""
    step_count, step_variables = _parse_step_variables(lines)

    warnings: list[str] = []
    measures: tuple[LogMeasurement, ...] = ()
    resolved_meas_path: Path | None = None
    qpost_command: tuple[str, ...] | None = None
    qpost_ran = False
    refreshed_measures = False

    if include_measures:
        resolved_meas_path = _resolve_meas_path(
            meas_path,
            workspace_root=normalized_workspace,
            default=log_path.with_suffix(".meas"),
        )
        if refresh_measures or not resolved_meas_path.is_file():
            netlist_path = _find_associated_netlist(log_path)
            if netlist_path is None:
                warnings.append(
                    "No sibling .net or .cir file was found, so QPOST measures "
                    "could not be refreshed."
                )
            else:
                qpost_path = _derive_qpost_path(effective_settings)
                staged_meas_path = build_staged_output_path(
                    resolved_meas_path,
                    label="qpost-tmp",
                )
                qpost_command = (str(qpost_path), str(netlist_path), "-o", str(staged_meas_path))
                staged_meas_path.parent.mkdir(parents=True, exist_ok=True)
                qpost_ran = True
                try:
                    process = run_subprocess(
                        qpost_command,
                        cwd=netlist_path.parent,
                        timeout_s=timeout_s,
                    )
                except subprocess.TimeoutExpired as exc:
                    discard_staged_output(staged_meas_path)
                    stderr = (
                        exc.stderr.decode("utf-8", errors="replace")
                        if isinstance(exc.stderr, bytes)
                        else exc.stderr
                    )
                    raise SimulationTimeoutError(
                        f"QPOST timed out after {timeout_s} seconds while materializing measures.",
                        stderr=stderr,
                    ) from exc
                if process.exit_code != 0:
                    discard_staged_output(staged_meas_path)
                    raise SimulationError(
                        "QPOST exited with a non-zero status while materializing measures.",
                        exit_code=process.exit_code,
                        stderr=process.stderr,
                    )
                if commit_staged_output(staged_meas_path, target_path=resolved_meas_path):
                    refreshed_measures = True
        if resolved_meas_path.is_file() and (not qpost_ran or refreshed_measures):
            measures = _parse_meas_file(resolved_meas_path, stepped=step_count > 0)
        else:
            warnings.append("No .meas file is available for this log yet.")

    return LogInspection(
        log_path=log_path,
        line_count=len(lines),
        excerpt=excerpt,
        step_count=step_count,
        step_variables=step_variables,
        measures=measures,
        meas_path=resolved_meas_path,
        qpost_command=qpost_command,
        warnings=tuple(warnings),
    )


__all__ = [
    "SERVICE_SPEC",
    "LogInspection",
    "LogMeasurement",
    "LogStepVariable",
    "read_log",
]
