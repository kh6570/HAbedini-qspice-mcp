"""Empty-workspace coverage for the bundled buck_converter_cpp recipe."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.materialize_reference_circuit import (
    materialize_reference_circuit,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_empty_workspace_materialize_path_writes_sibling_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "empty_buck"
    workspace.mkdir()

    result = materialize_reference_circuit(
        "buck_converter_cpp",
        workspace_root=workspace,
    )

    schematic = workspace / "Buck-converter.qsch"
    source = workspace / "buck_controller.cpp"
    assert schematic.is_file()
    assert source.is_file()
    assert schematic.parent == source.parent == workspace.resolve(strict=False)
    assert result.build_hint is not None
    assert "build_dll_device" in result.build_hint
