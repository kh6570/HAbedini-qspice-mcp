"""Tests for MCP recipe resource template registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from qspice_mcp.mcp.resources.registration import register_resource_templates

if TYPE_CHECKING:
    from pathlib import Path


def test_register_resource_templates_exposes_recipe_templates(tmp_path: Path) -> None:
    app = FastMCP("test")
    register_resource_templates(app, workspace_root=tmp_path)

    templates = app._resource_manager.list_templates()  # noqa: SLF001
    uri_templates = {template.uri_template for template in templates}
    assert "recipe://{recipe_id}/manifest" in uri_templates
    assert "recipe://{recipe_id}/schematic" in uri_templates
    assert "recipe://{recipe_id}/{document}" in uri_templates
