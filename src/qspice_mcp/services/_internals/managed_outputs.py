"""Shared helpers for transactional output artifact writes and restoration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class OutputBackup:
    """One backup record for a managed output artifact."""

    target_path: Path
    backup_path: Path | None


def build_staged_output_path(target_path: Path, *, label: str) -> Path:
    """Return one unique staged path for later promotion into `target_path`."""

    suffix = target_path.suffix
    token = uuid4().hex
    if suffix:
        staged_name = f"{target_path.stem}-{token}.{label}{suffix}"
    else:
        staged_name = f"{target_path.name}-{token}.{label}"
    return target_path.with_name(staged_name).resolve(strict=False)


def discard_staged_output(staged_path: Path) -> None:
    """Remove one staged artifact if it exists."""

    staged_path.unlink(missing_ok=True)


def commit_staged_output(staged_path: Path, *, target_path: Path) -> bool:
    """Promote one staged artifact into place if the staged file exists."""

    if not staged_path.is_file():
        return False
    staged_path.replace(target_path)
    return True


def write_text_via_stage(
    target_path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    stage_label: str,
) -> None:
    """Write text through a staged file so failed writes keep the prior target intact."""

    staged_path = build_staged_output_path(target_path, label=stage_label)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        staged_path.write_text(text, encoding=encoding)
        staged_path.replace(target_path)
    finally:
        discard_staged_output(staged_path)


def _backup_output_path(path: Path, *, label: str) -> Path | None:
    """Move one existing output aside so failures can restore it later."""

    if not path.is_file():
        return None
    backup_path = build_staged_output_path(path, label=label)
    path.replace(backup_path)
    return backup_path


def prepare_output_backups(paths: tuple[Path, ...], *, label: str) -> tuple[OutputBackup, ...]:
    """Capture the pre-write state for one or more output paths."""

    prepared: list[OutputBackup] = []
    seen: set[Path] = set()
    for path in paths:
        normalized = path.resolve(strict=False)
        if normalized in seen:
            continue
        seen.add(normalized)
        prepared.append(
            OutputBackup(
                target_path=normalized,
                backup_path=_backup_output_path(normalized, label=label),
            )
        )
    return tuple(prepared)


def restore_output_backups(backups: tuple[OutputBackup, ...]) -> None:
    """Discard partial replacement files and restore any pre-write artifacts."""

    for backup in backups:
        backup.target_path.unlink(missing_ok=True)
        if backup.backup_path is not None and backup.backup_path.exists():
            backup.backup_path.replace(backup.target_path)


def discard_output_backups(backups: tuple[OutputBackup, ...]) -> None:
    """Remove backup files once the new outputs have been accepted."""

    for backup in backups:
        if backup.backup_path is not None:
            backup.backup_path.unlink(missing_ok=True)


__all__ = [
    "OutputBackup",
    "build_staged_output_path",
    "commit_staged_output",
    "discard_output_backups",
    "discard_staged_output",
    "prepare_output_backups",
    "restore_output_backups",
    "write_text_via_stage",
]
