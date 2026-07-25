"""Register parameterized MCP resource templates."""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.recipes._catalog import (
    read_recipe_document,
    read_recipe_manifest_text,
    read_recipe_schematic_bytes,
)

if TYPE_CHECKING:
    from pathlib import Path

    from mcp.server.fastmcp import FastMCP

_REFERENCE_ROOT = "qspice_mcp.data.reference"
_REFERENCE_DOCUMENTS = {
    "directives": "qspice-directives.md",
}

_WORKSPACE_ARTIFACT_SUFFIXES = (
    ".qsch",
    ".net",
    ".cir",
    ".log",
    ".qraw",
    ".csv",
    ".json",
    ".md",
    ".txt",
)


def _decode_workspace_relpath(relpath: str) -> str:
    normalized = relpath.strip().replace("~", "/")
    if not normalized or normalized.startswith("/") or ".." in normalized.split("/"):
        raise ValueError("relpath must be a safe workspace-relative path.")
    return normalized


def read_workspace_artifact_bytes(relpath: str, *, workspace_root: Path) -> bytes:
    """Return one sandbox-validated workspace artifact as bytes."""

    resolved = resolve_workspace_path(
        _decode_workspace_relpath(relpath),
        workspace_root=workspace_root.resolve(strict=False),
    )
    if not resolved.is_file():
        raise FileNotFoundError(f"Workspace artifact not found: {relpath!r}")
    if resolved.suffix.lower() not in _WORKSPACE_ARTIFACT_SUFFIXES:
        allowed = ", ".join(_WORKSPACE_ARTIFACT_SUFFIXES)
        raise ValueError(f"Workspace artifact suffix must be one of: {allowed}")
    return resolved.read_bytes()


def reference_document_names() -> tuple[str, ...]:
    """Return the valid `reference://{document}` names."""

    return tuple(sorted(_REFERENCE_DOCUMENTS))


def read_reference_document(document: str) -> str:
    """Return one bundled agent-facing reference document as markdown text."""

    filename = _REFERENCE_DOCUMENTS.get(document.strip().lower())
    if filename is None:
        allowed = ", ".join(sorted(_REFERENCE_DOCUMENTS))
        raise ValueError(f"Unknown reference document {document!r}. Available: {allowed}")
    return files(_REFERENCE_ROOT).joinpath(filename).read_text(encoding="utf-8")


def register_resource_templates(app: FastMCP, *, workspace_root: Path) -> None:
    """Bind recipe and workspace artifact resource templates."""

    normalized_root = workspace_root.resolve(strict=False)

    @app.resource(
        "reference://{document}",
        name="reference_document",
        title="QSpice Reference Document",
        description=(
            "Return one bundled agent-facing QSpice reference document. "
            "Available: `directives` (netlist directive and `.options` cheatsheet)."
        ),
        mime_type="text/markdown",
    )
    def reference_document(document: str) -> str:
        return read_reference_document(document)

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

    @app.resource(
        "workspace-artifact://{relpath}",
        name="workspace_artifact",
        title="Workspace Artifact",
        description=(
            "Return one sandbox-validated workspace artifact. Nested paths use `~` "
            "instead of `/` (for example `artifacts~run1~out.qraw`)."
        ),
        mime_type="application/octet-stream",
    )
    def workspace_artifact(relpath: str) -> bytes:
        return read_workspace_artifact_bytes(relpath, workspace_root=normalized_root)


__all__ = [
    "read_reference_document",
    "read_workspace_artifact_bytes",
    "reference_document_names",
    "register_resource_templates",
]
