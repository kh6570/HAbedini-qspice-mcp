"""Tests for recipe resource template loaders."""

from __future__ import annotations

import json

from qspice_mcp.services.recipes._catalog import (
    read_recipe_document,
    read_recipe_manifest_text,
    read_recipe_schematic_bytes,
)


def test_read_recipe_manifest_text_returns_json_for_bundled_recipe() -> None:
    body = read_recipe_manifest_text("buck_converter_cpp")
    payload = json.loads(body)
    assert payload["recipe_id"] == "buck_converter_cpp"


def test_read_recipe_schematic_bytes_returns_qsch_payload() -> None:
    payload = read_recipe_schematic_bytes("buck_converter_cpp")
    assert len(payload) > 0


def test_read_recipe_document_returns_workflow_markdown() -> None:
    body = read_recipe_document("buck_converter_cpp", "scratch.md")
    assert "scratch" in body.lower() or "buck" in body.lower()
