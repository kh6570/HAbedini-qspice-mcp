"""Service staging a validated clean-room topology contribution into the workspace.

This does not mutate the bundled (package-data) knowledge pack. It validates a
candidate manifest, then writes the contribution (manifest, blueprint document, and a
ready-to-merge index entry) into a sandboxed ``topology_contributions/<block_id>/``
folder under the workspace so a maintainer can review and open a PR.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.topology._catalog import list_topology_index_entries
from qspice_mcp.services.topology.validate_topology_contribution import (
    validate_topology_contribution,
)

if TYPE_CHECKING:
    from pathlib import Path

_CONTRIBUTIONS_DIRNAME = "topology_contributions"


@dataclass(frozen=True, slots=True)
class TopologyContributionIngest:
    """Outcome of staging one topology-block contribution into the workspace."""

    block_id: str
    output_dir: Path
    written_files: tuple[Path, ...]
    is_valid: bool
    warnings: tuple[str, ...]
    collides_with_bundled_block: bool


SERVICE_SPEC = ServiceSpec(
    name="ingest_topology_contribution",
    title="Ingest Topology Contribution",
    summary=(
        "Validate a candidate topology-block manifest plus its blueprint and stage them "
        "(manifest.json, blueprint, index_entry.json) into a sandboxed "
        "topology_contributions/<block_id>/ folder under the workspace for PR review."
    ),
    phase="implemented",
    read_only=False,
)


def _require_bare_filename(document: str) -> str:
    """Ensure the manifest document is a bare file name (no path separators)."""

    if "/" in document or "\\" in document or document in {".", ".."}:
        raise ValidationError(
            "manifest['document'] must be a bare file name without path separators."
        )
    return document


def _index_entry_from_manifest(manifest: dict[str, Any], block_id: str) -> dict[str, Any]:
    raw_tags = manifest.get("tags", [])
    tags = (
        [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        if isinstance(raw_tags, list)
        else []
    )
    return {
        "block_id": block_id,
        "title": str(manifest.get("title", block_id)).strip(),
        "category": str(manifest.get("category", "")).strip(),
        "summary": str(manifest.get("summary", "")).strip(),
        "tags": tags,
        "directory": block_id,
    }


def ingest_topology_contribution(
    manifest: dict[str, Any],
    blueprint: str,
    *,
    workspace_root: Path,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
) -> TopologyContributionIngest:
    """Validate and stage a clean-room topology contribution into the workspace.

    Raises ``ValidationError`` (writing nothing) when the manifest fails validation, the
    blueprint is empty, or the manifest ``document`` is not a bare file name. On success
    it writes ``manifest.json``, the blueprint document, and ``index_entry.json`` into
    ``<output_dir or workspace>/topology_contributions/<block_id>/``.
    """

    validation = validate_topology_contribution(manifest)
    if not validation.is_valid or validation.block_id is None:
        joined = "; ".join(validation.errors) or "manifest failed validation."
        raise ValidationError(f"Invalid topology contribution: {joined}")
    block_id = validation.block_id

    if not blueprint.strip():
        raise ValidationError("blueprint must be a non-empty document.")

    document_name = _require_bare_filename(str(manifest["document"]).strip())

    base_dir = (
        resolve_workspace_path(output_dir, workspace_root=workspace_root)
        if output_dir is not None
        else workspace_root.resolve(strict=False)
    )
    destination = base_dir / _CONTRIBUTIONS_DIRNAME / block_id

    manifest_path = destination / "manifest.json"
    blueprint_path = destination / document_name
    index_entry_path = destination / "index_entry.json"
    targets = (manifest_path, blueprint_path, index_entry_path)

    if not overwrite:
        existing = [path for path in targets if path.exists()]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            raise ValidationError(
                f"Contribution files already exist (set overwrite=true): {joined}"
            )

    collides = any(entry.block_id == block_id for entry in list_topology_index_entries())
    warnings = list(validation.warnings)
    if collides:
        warnings.append(
            f"block_id {block_id!r} collides with a bundled topology block; "
            "choose a unique id before opening a PR."
        )

    destination.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    blueprint_path.write_text(blueprint, encoding="utf-8", newline="\n")
    index_entry_path.write_text(
        json.dumps(_index_entry_from_manifest(manifest, block_id), indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return TopologyContributionIngest(
        block_id=block_id,
        output_dir=destination,
        written_files=targets,
        is_valid=True,
        warnings=tuple(warnings),
        collides_with_bundled_block=collides,
    )


__all__ = [
    "SERVICE_SPEC",
    "TopologyContributionIngest",
    "ingest_topology_contribution",
]
