"""Tests for shared transactional output helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from qspice_mcp.services._internals.managed_outputs import (
    prepare_output_backups,
    restore_output_backups,
    write_text_via_stage,
)


def test_prepare_output_backups_restores_previous_content(tmp_path: Path) -> None:
    target = tmp_path / "demo.log"
    target.write_text("previous\n", encoding="utf-8")

    backups = prepare_output_backups((target, target), label="run-backup")

    assert len(backups) == 1
    assert target.exists() is False

    target.write_text("partial\n", encoding="utf-8")
    restore_output_backups(backups)

    assert target.read_text(encoding="utf-8") == "previous\n"


def test_write_text_via_stage_preserves_existing_target_on_write_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "artifact.txt"
    target.write_text("previous\n", encoding="utf-8")
    original_write_text = Path.write_text

    def fail_stage_write(
        self: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if self != target:
            original_write_text(
                self,
                "partial\n",
                encoding=encoding,
                errors=errors,
                newline=newline,
            )
            raise OSError("disk full")
        return original_write_text(
            self,
            data,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(Path, "write_text", fail_stage_write)

    with pytest.raises(OSError, match="disk full"):
        write_text_via_stage(
            target,
            "new\n",
            encoding="utf-8",
            stage_label="test-stage",
        )

    assert target.read_text(encoding="utf-8") == "previous\n"
    assert list(tmp_path.glob("artifact-*.test-stage.txt")) == []
