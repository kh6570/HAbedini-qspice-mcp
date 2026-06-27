"""Unit tests for the topology contribution ingestion service."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

from qspice_mcp.core.exceptions import SandboxViolationError, ValidationError
from qspice_mcp.services.topology._catalog import (
    clear_topology_root_cache,
    load_topology_manifest,
    read_topology_document,
)
from qspice_mcp.services.topology.ingest_topology_contribution import (
    ingest_topology_contribution,
)

if TYPE_CHECKING:
    from pathlib import Path

_BLUEPRINT = "# SEPIC converter\n\nClean-room blueprint for a SEPIC stage.\n"


def _valid_manifest(block_id: str = "sepic_converter") -> dict[str, Any]:
    return {
        "block_id": block_id,
        "title": "SEPIC Converter",
        "category": "non_isolated_dc_dc",
        "summary": "Single-ended primary-inductance converter for step-up/step-down.",
        "tags": ["sepic", "step-up", "step-down"],
        "ports": [
            {"name": "in", "role": "input", "description": "Input supply rail."},
            {"name": "out", "role": "output", "description": "Regulated output rail."},
        ],
        "parameters": [
            {"name": "Vin", "description": "Input voltage.", "unit": "V"},
            {"name": "Vout", "description": "Output voltage.", "unit": "V"},
        ],
        "design_equations": [
            {
                "name": "conversion_ratio",
                "expression": "Vout/Vin = D/(1-D)",
                "description": "Ideal CCM conversion ratio.",
            }
        ],
        "control_notes": "Fourth-order plant; current-mode control recommended.",
        "reference": {"source": "Clean-room derivation", "isbn": "000-0000000000"},
        "document": "blueprint.md",
    }


def test_ingest_writes_contribution_files(tmp_path: Path) -> None:
    result = ingest_topology_contribution(_valid_manifest(), _BLUEPRINT, workspace_root=tmp_path)

    assert result.is_valid is True
    assert result.collides_with_bundled_block is False
    staged = tmp_path / "topology_contributions" / "sepic_converter"
    assert (staged / "manifest.json").is_file()
    assert (staged / "blueprint.md").read_text(encoding="utf-8") == _BLUEPRINT
    index_entry = json.loads((staged / "index_entry.json").read_text(encoding="utf-8"))
    assert index_entry["block_id"] == "sepic_converter"
    assert index_entry["directory"] == "sepic_converter"


def test_ingest_rejects_invalid_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="Invalid topology contribution"):
        ingest_topology_contribution({"block_id": "broken"}, _BLUEPRINT, workspace_root=tmp_path)
    assert not (tmp_path / "topology_contributions").exists()


def test_ingest_rejects_empty_blueprint(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="blueprint"):
        ingest_topology_contribution(_valid_manifest(), "   ", workspace_root=tmp_path)


def test_ingest_rejects_document_with_path_separators(tmp_path: Path) -> None:
    manifest = _valid_manifest()
    manifest["document"] = "../escape.md"
    with pytest.raises(ValidationError, match="bare file name"):
        ingest_topology_contribution(manifest, _BLUEPRINT, workspace_root=tmp_path)


def test_ingest_rejects_sandbox_escape(tmp_path: Path) -> None:
    with pytest.raises(SandboxViolationError):
        ingest_topology_contribution(
            _valid_manifest(), _BLUEPRINT, workspace_root=tmp_path, output_dir="../outside"
        )


def test_ingest_warns_on_bundled_collision(tmp_path: Path) -> None:
    result = ingest_topology_contribution(
        _valid_manifest("buck_converter"), _BLUEPRINT, workspace_root=tmp_path
    )
    assert result.collides_with_bundled_block is True
    assert any("collides" in warning for warning in result.warnings)


def test_ingest_requires_overwrite_for_existing(tmp_path: Path) -> None:
    ingest_topology_contribution(_valid_manifest(), _BLUEPRINT, workspace_root=tmp_path)
    with pytest.raises(ValidationError, match="already exist"):
        ingest_topology_contribution(_valid_manifest(), _BLUEPRINT, workspace_root=tmp_path)
    # overwrite=True succeeds.
    result = ingest_topology_contribution(
        _valid_manifest(), _BLUEPRINT, workspace_root=tmp_path, overwrite=True
    )
    assert result.is_valid is True


def test_ingested_contribution_round_trips_through_topology_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ingest_topology_contribution(_valid_manifest(), _BLUEPRINT, workspace_root=tmp_path)
    contributions_root = tmp_path / "topology_contributions"
    index_entry = json.loads(
        (contributions_root / "sepic_converter" / "index_entry.json").read_text(encoding="utf-8")
    )
    (contributions_root / "index.json").write_text(
        json.dumps({"blocks": [index_entry]}, indent=2), encoding="utf-8"
    )

    monkeypatch.setenv("QSPICE_TOPOLOGY_PATH", str(contributions_root))
    clear_topology_root_cache()
    try:
        manifest = load_topology_manifest("sepic_converter")
        assert manifest["title"] == "SEPIC Converter"
        document = read_topology_document("sepic_converter", "blueprint.md")
        assert "SEPIC converter" in document
    finally:
        monkeypatch.delenv("QSPICE_TOPOLOGY_PATH", raising=False)
        clear_topology_root_cache()
