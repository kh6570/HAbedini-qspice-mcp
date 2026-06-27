"""Load the bundled composable topology knowledge pack from package data."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import ValidationError

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

_TOPOLOGY_ROOT = "qspice_mcp.data.topology"
_TOPOLOGY_PATH_ENV = "QSPICE_TOPOLOGY_PATH"


@dataclass(frozen=True, slots=True)
class TopologyIndexEntry:
    """One topology block row from the top-level catalog index."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    directory: str


@cache
def _topology_root() -> Traversable:
    override = os.environ.get(_TOPOLOGY_PATH_ENV, "").strip()
    if override:
        override_path = Path(override).expanduser()
        if override_path.is_dir():
            return override_path
        raise ValidationError(
            f"{_TOPOLOGY_PATH_ENV} is set to {override!r} but that directory does not exist."
        )
    return files(_TOPOLOGY_ROOT)


def clear_topology_root_cache() -> None:
    """Clear memoized topology-root and manifest resolution (primarily for tests)."""

    _topology_root.cache_clear()
    load_topology_index.cache_clear()
    load_topology_manifest.cache_clear()
    # Local import avoids a module-level import cycle (_search_index imports this module).
    from qspice_mcp.services.topology._search_index import (  # noqa: PLC0415
        clear_search_index_cache,
    )

    clear_search_index_cache()


@cache
def load_topology_index() -> dict[str, Any]:
    """Load and lightly validate the topology index document."""

    index_path = _topology_root() / "index.json"
    try:
        payload: dict[str, Any] = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError("Topology index is missing from package data.") from exc
    if not isinstance(payload.get("blocks"), list):
        raise ValidationError("Topology index must include a blocks array.")
    return payload


def topology_attribution() -> dict[str, Any]:
    """Return the attribution block recorded in the topology index."""

    attribution = load_topology_index().get("attribution")
    return dict(attribution) if isinstance(attribution, dict) else {}


def list_topology_index_entries() -> tuple[TopologyIndexEntry, ...]:
    """Return every topology block listed in the catalog index."""

    payload = load_topology_index()
    entries: list[TopologyIndexEntry] = []
    for raw_entry in payload["blocks"]:
        if not isinstance(raw_entry, dict):
            raise ValidationError("Each topology index entry must be a JSON object.")
        block_id = str(raw_entry.get("block_id", "")).strip()
        if not block_id:
            raise ValidationError("Topology index entries require block_id.")
        raw_tags = raw_entry.get("tags", [])
        tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
        entries.append(
            TopologyIndexEntry(
                block_id=block_id,
                title=str(raw_entry.get("title", block_id)).strip(),
                category=str(raw_entry.get("category", "")).strip(),
                summary=str(raw_entry.get("summary", "")).strip(),
                tags=tags,
                directory=str(raw_entry.get("directory", block_id)).strip() or block_id,
            )
        )
    return tuple(entries)


def _resolve_block_directory(block_id: str) -> str:
    for entry in list_topology_index_entries():
        if entry.block_id == block_id:
            return entry.directory
    known = ", ".join(entry.block_id for entry in list_topology_index_entries())
    raise ValidationError(
        f"Unknown topology block_id: {block_id!r}. Known blocks: {known or '(none)'}"
    )


@cache
def load_topology_manifest(block_id: str) -> dict[str, Any]:
    """Load and validate one topology block manifest."""

    normalized_block_id = block_id.strip()
    if not normalized_block_id:
        raise ValidationError("block_id must not be empty.")

    directory = _resolve_block_directory(normalized_block_id)
    manifest_path = _topology_root() / directory / "manifest.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"Topology manifest missing for {block_id!r}.") from exc

    manifest: dict[str, Any] = json.loads(manifest_text)
    if str(manifest.get("block_id", "")).strip() != normalized_block_id:
        raise ValidationError(
            f"Topology manifest block_id mismatch: expected {normalized_block_id!r}, "
            f"got {manifest.get('block_id')!r}"
        )
    return manifest


def read_topology_document(block_id: str, document: str) -> str:
    """Read one bundled topology document (for example a block blueprint)."""

    normalized_document = document.strip()
    if not normalized_document:
        raise ValidationError("document must not be empty.")
    if "/" in normalized_document or "\\" in normalized_document:
        raise ValidationError("document must be a bundle file name without path separators.")
    directory = _resolve_block_directory(block_id.strip())
    document_path = _topology_root() / directory / normalized_document
    try:
        return document_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Topology document missing for {block_id!r}: {normalized_document!r}"
        ) from exc


__all__ = [
    "TopologyIndexEntry",
    "clear_topology_root_cache",
    "list_topology_index_entries",
    "load_topology_index",
    "load_topology_manifest",
    "read_topology_document",
    "topology_attribution",
]
