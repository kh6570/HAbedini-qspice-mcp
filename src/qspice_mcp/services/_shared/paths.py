"""Validation helpers shared by application services."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.core.exceptions import (
    ArtifactMissingError,
    SandboxViolationError,
    ValidationError,
)


def resolve_workspace_path(raw_path: str | Path, *, workspace_root: Path) -> Path:
    """Resolve a relative or absolute path inside the configured workspace root."""

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate

    resolved = candidate.resolve(strict=False)
    root = workspace_root.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise SandboxViolationError(f"Path is outside workspace root: {resolved}")
    return resolved


def validate_existing_file(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    suffixes: tuple[str, ...] = (),
) -> Path:
    """Resolve and validate an existing file within the workspace root."""

    resolved = resolve_workspace_path(raw_path, workspace_root=workspace_root)
    normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
    if normalized_suffixes and resolved.suffix.lower() not in normalized_suffixes:
        suffix_list = ", ".join(normalized_suffixes)
        raise ValidationError(f"Expected one of {suffix_list}, got {resolved.suffix!r}")
    if not resolved.is_file():
        raise ArtifactMissingError(f"File not found: {resolved}")
    return resolved


def resolve_workspace_output_path(
    raw_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
    suffixes: tuple[str, ...],
) -> Path:
    """Resolve one writable output path and require an explicit allowed suffix."""

    if raw_path is None:
        return default.resolve(strict=False)

    resolved = resolve_workspace_path(raw_path, workspace_root=workspace_root)
    normalized_suffixes = tuple(suffix.lower() for suffix in suffixes)
    if normalized_suffixes and not any(
        resolved.name.lower().endswith(suffix) for suffix in normalized_suffixes
    ):
        suffix_list = ", ".join(normalized_suffixes)
        raise ValidationError(f"Output path must end in one of: {suffix_list}")
    return resolved


def validate_time_window(
    t_start: float | None,
    t_end: float | None,
) -> tuple[float | None, float | None]:
    """Validate an optional waveform time window."""

    if t_start is not None and t_end is not None and t_end < t_start:
        raise ValidationError("t_end must be greater than or equal to t_start")
    return t_start, t_end
