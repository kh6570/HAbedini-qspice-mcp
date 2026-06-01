"""Regression tests for no-backend schematic-editor loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends import schematic_editor_backend

if TYPE_CHECKING:
    from pathlib import Path


def test_open_schematic_editor_raises_backend_unavailable_when_no_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    monkeypatch.setattr(
        schematic_editor_backend,
        "load_qsch_editor_factory",
        lambda: (None, None),
    )

    with pytest.raises(BackendUnavailableError, match="No compatible local QschEditor backend"):
        schematic_editor_backend.open_schematic_editor(schematic, workspace_root=tmp_path)
