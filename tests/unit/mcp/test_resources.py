"""Tests for packaged MCP resource content."""

from __future__ import annotations

from qspice_mcp.mcp.resources import get_resource_content, get_resource_definitions


def test_all_defined_resources_have_packaged_markdown_bodies() -> None:
    resources = get_resource_definitions()

    assert resources
    for resource in resources:
        body = get_resource_content(resource.uri)

        assert body is not None
        assert body.startswith("# ")
        assert body != resource.description
        assert len(body) > len(resource.description)
