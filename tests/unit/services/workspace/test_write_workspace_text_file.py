"""Tests for write_workspace_text_file service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import SandboxViolationError, ValidationError
from qspice_mcp.services.workspace.write_workspace_text_file import write_workspace_text_file

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("suffix", [".cpp", ".cc", ".cxx"])
def test_write_workspace_text_file_writes_cpp(tmp_path: Path, suffix: str) -> None:
    result = write_workspace_text_file(
        f"buck_controller{suffix}",
        workspace_root=tmp_path,
        content="// test\n",
        overwrite=False,
    )

    assert result.output_path == tmp_path / f"buck_controller{suffix}"
    assert result.output_path.read_text(encoding="utf-8") == "// test\n"
    assert result.line_count == 2


def test_write_workspace_text_file_rejects_overwrite_without_flag(tmp_path: Path) -> None:
    write_workspace_text_file("device.cpp", workspace_root=tmp_path, content="// x\n")
    with pytest.raises(ValidationError, match="overwrite=true"):
        write_workspace_text_file("device.cpp", workspace_root=tmp_path, content="// y\n")


def test_write_workspace_text_file_writes_and_overwrites_layout_json(tmp_path: Path) -> None:
    content = '{\n  "schema_version": 1,\n  "components": []\n}'
    result = write_workspace_text_file(
        "artifacts/layout.json", workspace_root=tmp_path, content=content
    )
    assert result.output_path.read_bytes() == content.encode("utf-8")
    assert result.overwritten is False
    with pytest.raises(ValidationError, match="overwrite=true"):
        write_workspace_text_file("artifacts/layout.json", workspace_root=tmp_path, content="{}")
    overwritten = write_workspace_text_file(
        "artifacts/layout.json", workspace_root=tmp_path, content="{}", overwrite=True
    )
    assert overwritten.overwritten is True
    assert overwritten.output_path.read_bytes() == b"{}"


def test_json_write_cannot_escape_workspace(tmp_path: Path) -> None:
    with pytest.raises(SandboxViolationError, match="outside"):
        write_workspace_text_file("../escape.json", workspace_root=tmp_path, content="{}")


def test_text_writer_still_rejects_schematic_files(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Output path must end"):
        write_workspace_text_file("circuit.qsch", workspace_root=tmp_path, content="{}")
