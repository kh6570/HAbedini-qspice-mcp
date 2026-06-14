"""Tests for write_workspace_text_file service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.workspace.write_workspace_text_file import write_workspace_text_file

if TYPE_CHECKING:
    from pathlib import Path


def test_write_workspace_text_file_writes_cpp(tmp_path: Path) -> None:
    result = write_workspace_text_file(
        "buck_controller.cpp",
        workspace_root=tmp_path,
        content="// test\n",
        overwrite=False,
    )

    assert result.output_path == tmp_path / "buck_controller.cpp"
    assert result.output_path.read_text(encoding="utf-8") == "// test\n"
    assert result.line_count == 2


def test_write_workspace_text_file_rejects_overwrite_without_flag(tmp_path: Path) -> None:
    write_workspace_text_file("device.cpp", workspace_root=tmp_path, content="// x\n")
    with pytest.raises(ValidationError, match="overwrite=true"):
        write_workspace_text_file("device.cpp", workspace_root=tmp_path, content="// y\n")
