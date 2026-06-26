"""Tests for the render_schematic_image service."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.render_schematic_image import render_schematic_image

if TYPE_CHECKING:
    from pathlib import Path


def test_render_schematic_image_writes_png(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)

    result = render_schematic_image(schematic, workspace_root=tmp_path)

    assert result.image_path.is_file()
    assert result.image_path.suffix == ".png"
    assert result.format == "png"
    assert result.component_count == 2
    assert result.wire_count >= 1


def test_render_schematic_image_refuses_overwrite(tmp_path: Path) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)
    image = tmp_path / "preview.png"

    render_schematic_image(schematic, workspace_root=tmp_path, output_path=image)

    with pytest.raises(FileExistsError):
        render_schematic_image(schematic, workspace_root=tmp_path, output_path=image)
