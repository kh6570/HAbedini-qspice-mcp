# In the name of God, the Most Gracious, the Most Merciful
"""Workspace path checks. The rules live in mcp-app-core."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_app_core.paths import resolve_output_path as _resolve_output_path
from mcp_app_core.paths import resolve_workspace_path as _resolve_workspace_path
from mcp_app_core.paths import validate_existing_file as _validate_existing_file
from mcp_app_core.paths import validate_time_window as _validate_time_window

from qspice_mcp.core.exceptions import (
    ArtifactMissingError,
    SandboxViolationError,
    ValidationError,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sandbox_message(exc: SandboxViolationError, workspace_root: Path) -> str:
    """Add the active root and the way to select another circuit folder."""

    root = workspace_root.resolve(strict=False)
    return (
        f"{exc}. Active workspace root: {root}. Absolute paths must also stay inside this root. "
        "To access a different circuit folder, pass workspace_root explicitly "
        "for that folder and use an absolute path or a path relative to it."
    )


def resolve_workspace_path(raw_path: str | Path, *, workspace_root: Path) -> Path:
    """Resolve a relative or absolute path inside the configured workspace root."""

    try:
        return _resolve_workspace_path(
            raw_path, workspace_root=workspace_root, sandbox_error=SandboxViolationError
        )
    except SandboxViolationError as exc:
        raise SandboxViolationError(_sandbox_message(exc, workspace_root)) from exc


def validate_existing_file(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    suffixes: tuple[str, ...] = (),
) -> Path:
    """Resolve and validate an existing file within the workspace root."""

    try:
        return _validate_existing_file(
            raw_path,
            workspace_root=workspace_root,
            suffixes=suffixes,
            sandbox_error=SandboxViolationError,
            validation_error=ValidationError,
            missing_error=ArtifactMissingError,
        )
    except SandboxViolationError as exc:
        raise SandboxViolationError(_sandbox_message(exc, workspace_root)) from exc


def resolve_workspace_output_path(
    raw_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
    suffixes: tuple[str, ...],
) -> Path:
    """Resolve one writable output path and require an explicit allowed suffix."""

    try:
        return _resolve_output_path(
            raw_path,
            workspace_root=workspace_root,
            default=default,
            suffixes=suffixes,
            sandbox_error=SandboxViolationError,
            validation_error=ValidationError,
        )
    except SandboxViolationError as exc:
        raise SandboxViolationError(_sandbox_message(exc, workspace_root)) from exc


def validate_time_window(
    t_start: float | None,
    t_end: float | None,
) -> tuple[float | None, float | None]:
    """Validate an optional waveform time window."""

    return _validate_time_window(t_start, t_end, validation_error=ValidationError)
