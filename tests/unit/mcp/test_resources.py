# In the name of God, the Most Gracious, the Most Merciful
"""Tests for packaged MCP resource content."""

from __future__ import annotations

from qspice_mcp.mcp.resources import get_resource_content, get_resource_definitions

_OPENING_LINE = "In the name of God, the Most Gracious, the Most Merciful"


def _markdown_after_opening(body: str) -> str:
    """Return the document after the required opening line, when it is present."""

    if body.startswith(_OPENING_LINE):
        return body[len(_OPENING_LINE) :].lstrip("\r\n")
    return body


def test_all_defined_resources_have_packaged_markdown_bodies() -> None:
    resources = get_resource_definitions()

    assert resources
    for resource in resources:
        body = get_resource_content(resource.uri)

        assert body is not None
        assert _markdown_after_opening(body).startswith("# ")
        assert body != resource.description
        assert len(body) > len(resource.description)
