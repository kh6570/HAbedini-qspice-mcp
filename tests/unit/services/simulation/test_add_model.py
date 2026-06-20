"""Tests for model definition authoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.simulation.add_model import add_model

if TYPE_CHECKING:
    from pathlib import Path


def test_add_model_appends_definition(tmp_path: Path) -> None:
    library = tmp_path / "devices.lib"
    library.write_text("* devices\n.end\n", encoding="utf-8")
    model_text = ".model NMOS1 NMOS (VTO=1 KP=20u)\n"

    result = add_model(
        library,
        workspace_root=tmp_path,
        model_text=model_text,
    )

    updated = result.output_path.read_text(encoding="utf-8")
    assert ".model NMOS1 NMOS" in updated
    assert result.model_name == "NMOS1"
    assert result.line_count == 1


def test_add_model_rejects_end_directive(tmp_path: Path) -> None:
    library = tmp_path / "devices.lib"
    library.write_text("* devices\n.end\n", encoding="utf-8")

    with pytest.raises(ValidationError, match=r"\.end"):
        add_model(
            library,
            workspace_root=tmp_path,
            model_text=".model X D\n.end\n",
        )
