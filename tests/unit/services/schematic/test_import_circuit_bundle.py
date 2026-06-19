"""Tests for schematic bundle import."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.schematic.import_circuit_bundle import import_circuit_bundle

if TYPE_CHECKING:
    from pathlib import Path


def test_import_circuit_bundle_copies_schematic_and_sidecars(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    schematic = source_dir / "demo.qsch"
    schematic.write_bytes(b"qsch")
    controller = source_dir / "demo.cpp"
    controller.write_text("int main() {}", encoding="utf-8")
    artifact = source_dir / "demo.log"
    artifact.write_text("log", encoding="utf-8")
    destination = tmp_path / "imported"

    result = import_circuit_bundle(
        schematic,
        workspace_root=tmp_path,
        output_dir=destination,
    )

    copied_names = {entry.relative_path for entry in result.files}
    assert copied_names == {"demo.qsch", "demo.cpp"}
    assert (destination / "demo.qsch").is_file()
    assert (destination / "demo.cpp").is_file()


def test_import_circuit_bundle_rejects_existing_without_overwrite(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    schematic = source_dir / "demo.qsch"
    schematic.write_bytes(b"qsch")
    destination = tmp_path / "dest"
    destination.mkdir()
    (destination / "demo.qsch").write_bytes(b"existing")

    with pytest.raises(ValidationError):
        import_circuit_bundle(
            schematic,
            workspace_root=tmp_path,
            output_dir=destination,
            overwrite=False,
        )
