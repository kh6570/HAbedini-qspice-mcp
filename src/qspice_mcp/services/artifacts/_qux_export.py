"""Shared helpers for QUX-backed export services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.managed_outputs import write_text_via_stage
from qspice_mcp.services._internals.qux import (
    QuxExportFormat,
    build_dll_variables_command,
    build_qux_export_command,
    resolve_qux_companion,
    run_qux_command,
)
from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
    validate_existing_file,
)

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

_EXPORT_SUFFIXES: dict[QuxExportFormat, str] = {
    "ascii": ".ascii.txt",
    "csv": ".csv",
    "s2p": ".s2p",
    "spice": ".spice.txt",
}


@dataclass(frozen=True, slots=True)
class QuxWaveformExport:
    """Metadata for one QUX-backed waveform export artifact."""

    raw_path: Path
    qux_path: Path
    output_path: Path
    format: str
    expressions: tuple[str, ...]
    point_count: int | None
    line_count: int
    command: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DllVariableExport:
    """Metadata for one generated `.DLL` variable-declaration artifact."""

    schematic_path: Path
    qux_path: Path
    output_path: Path
    line_count: int
    command: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def _count_lines(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def _resolve_export_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    source_path: Path,
    suffix: str,
) -> Path:
    return resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=source_path.with_name(f"{source_path.stem}-export{suffix}"),
        suffixes=(suffix,),
    )


def export_waveform_with_qux(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    expressions: tuple[str, ...] | list[str],
    export_format: QuxExportFormat,
    point_count: int | None = None,
    output_path: str | Path | None = None,
) -> QuxWaveformExport:
    """Export waveform expressions through the documented `QUX.exe -Export` path."""

    workspace = workspace_root.resolve(strict=False)
    resolved_raw_path = validate_existing_file(
        raw_path, workspace_root=workspace, suffixes=(".qraw",)
    )
    normalized_expressions = tuple(
        expression.strip() for expression in expressions if expression.strip()
    )
    destination = _resolve_export_output_path(
        output_path,
        workspace_root=workspace,
        source_path=resolved_raw_path,
        suffix=_EXPORT_SUFFIXES[export_format],
    )
    companion = resolve_qux_companion(settings)
    command = build_qux_export_command(
        companion.qux_path,
        resolved_raw_path,
        expressions=normalized_expressions,
        export_format=export_format,
        point_count=point_count,
        stdout=True,
    )
    result = run_qux_command(command, cwd=resolved_raw_path.parent)
    write_text_via_stage(destination, result.stdout, encoding="utf-8", stage_label="qux-output")
    return QuxWaveformExport(
        raw_path=resolved_raw_path,
        qux_path=companion.qux_path,
        output_path=destination,
        format=export_format.upper(),
        expressions=normalized_expressions,
        point_count=point_count,
        line_count=_count_lines(result.stdout),
        command=command,
    )


def generate_dll_variables_with_qux(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    output_path: str | Path | None = None,
) -> DllVariableExport:
    """Generate `.DLL` variable declarations through `QUX.exe -DLLvariables`."""

    workspace = workspace_root.resolve(strict=False)
    resolved_schematic_path = validate_existing_file(
        schematic_path,
        workspace_root=workspace,
        suffixes=(".qsch",),
    )
    destination = _resolve_export_output_path(
        output_path,
        workspace_root=workspace,
        source_path=resolved_schematic_path,
        suffix=".dllvars.txt",
    )
    companion = resolve_qux_companion(settings)
    command = build_dll_variables_command(
        companion.qux_path,
        resolved_schematic_path,
        stdout=True,
    )
    result = run_qux_command(command, cwd=resolved_schematic_path.parent)
    write_text_via_stage(destination, result.stdout, encoding="utf-8", stage_label="qux-output")
    return DllVariableExport(
        schematic_path=resolved_schematic_path,
        qux_path=companion.qux_path,
        output_path=destination,
        line_count=_count_lines(result.stdout),
        command=command,
    )


__all__ = [
    "DllVariableExport",
    "QuxWaveformExport",
    "export_waveform_with_qux",
    "generate_dll_variables_with_qux",
]
