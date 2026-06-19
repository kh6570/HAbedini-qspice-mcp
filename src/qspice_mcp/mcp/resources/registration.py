"""Register parameterized MCP resource templates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.recipes._catalog import (
    read_recipe_document,
    read_recipe_manifest_text,
    read_recipe_schematic_bytes,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mcp.server.fastmcp import FastMCP


def register_resource_templates(app: FastMCP, *, workspace_root: Path) -> None:
    """Bind recipe and workspace artifact resource templates."""

    del workspace_root

    @app.resource(
        "recipe://{recipe_id}/manifest",
        name="recipe_manifest",
        title="Recipe Manifest",
        description="Return the JSON manifest for one bundled reference-circuit recipe.",
        mime_type="application/json",
    )
    def recipe_manifest(recipe_id: str) -> str:
        return read_recipe_manifest_text(recipe_id)

    @app.resource(
        "recipe://{recipe_id}/schematic",
        name="recipe_schematic",
        title="Recipe Schematic",
        description="Return the bundled `.qsch` bytes for one reference-circuit recipe.",
        mime_type="application/octet-stream",
    )
    def recipe_schematic(recipe_id: str) -> bytes:
        return read_recipe_schematic_bytes(recipe_id)

    @app.resource(
        "recipe://{recipe_id}/{document}",
        name="recipe_document",
        title="Recipe Document",
        description=(
            "Return one bundled recipe document such as a workflow markdown file "
            "(for example `scratch.md` or `catalog.md`)."
        ),
        mime_type="text/markdown",
    )
    def recipe_document(recipe_id: str, document: str) -> str:
        return read_recipe_document(recipe_id, document)


__all__ = ["register_resource_templates"]
