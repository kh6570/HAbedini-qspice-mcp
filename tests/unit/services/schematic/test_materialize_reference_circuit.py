"""Tests for materialize_reference_circuit service."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.schematic.materialize_reference_circuit import (
    materialize_reference_circuit,
)

if TYPE_CHECKING:
    from pathlib import Path

_BUNDLE_ROOT = files("qspice_mcp.data.recipes") / "buck_converter_cpp"


def test_materialize_buck_converter_cpp_writes_expected_files(tmp_path: Path) -> None:
    result = materialize_reference_circuit(
        "buck_converter_cpp",
        workspace_root=tmp_path,
    )

    assert result.recipe_id == "buck_converter_cpp"
    assert result.build_required is True
    assert result.output_dir == tmp_path.resolve(strict=False)
    assert len(result.files) == 2

    schematic = tmp_path / "Buck-converter.qsch"
    source = tmp_path / "buck_controller.cpp"
    assert schematic.is_file()
    assert source.is_file()

    assert schematic.read_bytes() == (_BUNDLE_ROOT / "Buck-converter.qsch").read_bytes()
    assert source.read_text(encoding="utf-8") == (_BUNDLE_ROOT / "buck_controller.cpp").read_text(
        encoding="utf-8"
    )


def test_materialize_rejects_unknown_recipe(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Unknown recipe_id"):
        materialize_reference_circuit("not_a_recipe", workspace_root=tmp_path)


def test_materialize_honors_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "buck_run"
    result = materialize_reference_circuit(
        "buck_converter_cpp",
        workspace_root=tmp_path,
        output_dir=output_dir,
    )

    assert result.output_dir == output_dir.resolve(strict=False)
    assert (output_dir / "Buck-converter.qsch").is_file()
    assert (output_dir / "buck_controller.cpp").is_file()


def test_materialize_refuses_overwrite_without_flag(tmp_path: Path) -> None:
    materialize_reference_circuit("buck_converter_cpp", workspace_root=tmp_path)
    with pytest.raises(ValidationError, match="overwrite=true"):
        materialize_reference_circuit("buck_converter_cpp", workspace_root=tmp_path)


def test_materialize_allows_overwrite(tmp_path: Path) -> None:
    first = materialize_reference_circuit("buck_converter_cpp", workspace_root=tmp_path)
    second = materialize_reference_circuit(
        "buck_converter_cpp",
        workspace_root=tmp_path,
        overwrite=True,
    )
    assert first.files[0].overwritten is False
    assert second.files[0].overwritten is True
