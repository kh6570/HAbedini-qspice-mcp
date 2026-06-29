"""Unit tests for the bundled topology knowledge-pack catalog loader."""

from __future__ import annotations

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.topology._catalog import (
    list_topology_index_entries,
    load_topology_manifest,
    read_topology_document,
    topology_attribution,
)

_EXPECTED_BLOCK_IDS = {
    "buck_converter",
    "boost_converter",
    "buck_boost_converter",
    "flyback_converter",
    "forward_converter",
}
_EXPECTED_CATEGORIES = {
    "buck_converter": "non_isolated_dc_dc",
    "boost_converter": "non_isolated_dc_dc",
    "buck_boost_converter": "non_isolated_dc_dc",
    "flyback_converter": "isolated_dc_dc",
    "forward_converter": "isolated_dc_dc",
}


def test_index_entries_cover_expected_blocks() -> None:
    entries = list_topology_index_entries()
    assert {entry.block_id for entry in entries} == _EXPECTED_BLOCK_IDS
    for entry in entries:
        assert entry.title
        assert entry.category == _EXPECTED_CATEGORIES[entry.block_id]
        assert entry.tags
        assert entry.summary


def test_attribution_cites_reference_with_clean_room_note() -> None:
    attribution = topology_attribution()
    primary = attribution["primary_reference"]
    assert primary["isbn"] == "979-8278321743"
    assert "clean-room" in primary["note"].lower()


@pytest.mark.parametrize("block_id", sorted(_EXPECTED_BLOCK_IDS))
def test_load_manifest_round_trips_block_id(block_id: str) -> None:
    manifest = load_topology_manifest(block_id)
    assert manifest["block_id"] == block_id
    assert manifest["design_equations"]
    assert manifest["reference"]["source"].startswith("J. Marcos Alonso")


def test_load_manifest_rejects_unknown_block() -> None:
    with pytest.raises(ValidationError, match="Unknown topology block_id"):
        load_topology_manifest("not_a_block")


def test_load_manifest_rejects_empty_block_id() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        load_topology_manifest("   ")


def test_read_document_returns_blueprint_text() -> None:
    text = read_topology_document("buck_converter", "blueprint.md")
    assert "Buck converter" in text
    assert "clean-room" in text.lower()


def test_read_document_rejects_path_separators() -> None:
    with pytest.raises(ValidationError, match="without path separators"):
        read_topology_document("buck_converter", "../secret.md")


def test_read_document_rejects_missing_file() -> None:
    with pytest.raises(ValidationError, match="Topology document missing"):
        read_topology_document("buck_converter", "nope.md")
