"""Service listing bundled composable topology blocks from package data."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.topology._catalog import (
    list_topology_index_entries,
    topology_attribution,
)


@dataclass(frozen=True, slots=True)
class TopologyBlockSummary:
    """One topology block row for discovery responses."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TopologyBlockCatalog:
    """The full list of bundled topology blocks plus pack attribution."""

    blocks: tuple[TopologyBlockSummary, ...]
    attribution: dict[str, object]


SERVICE_SPEC = ServiceSpec(
    name="list_topology_blocks",
    title="List Topology Blocks",
    summary="List bundled composable DC-DC converter topology blocks from the knowledge pack.",
    phase="implemented",
    read_only=True,
)


def list_topology_blocks() -> TopologyBlockCatalog:
    """Return every bundled topology block summary and the pack attribution."""

    blocks = tuple(
        TopologyBlockSummary(
            block_id=entry.block_id,
            title=entry.title,
            category=entry.category,
            summary=entry.summary,
            tags=entry.tags,
        )
        for entry in list_topology_index_entries()
    )
    return TopologyBlockCatalog(blocks=blocks, attribution=topology_attribution())


__all__ = ["SERVICE_SPEC", "TopologyBlockCatalog", "TopologyBlockSummary", "list_topology_blocks"]
