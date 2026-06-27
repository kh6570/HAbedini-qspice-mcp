"""Service returning one topology block manifest plus its blueprint document."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.topology._catalog import (
    load_topology_manifest,
    read_topology_document,
    topology_attribution,
)


@dataclass(frozen=True, slots=True)
class TopologyBlockDetail:
    """One topology block manifest, blueprint text, and pack attribution."""

    block_id: str
    title: str
    category: str
    summary: str
    tags: tuple[str, ...]
    ports: tuple[dict[str, Any], ...]
    parameters: tuple[dict[str, Any], ...]
    design_equations: tuple[dict[str, Any], ...]
    control_notes: str
    reference: dict[str, Any]
    document_name: str
    document: str
    attribution: dict[str, object]


def _as_dict_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, dict))


SERVICE_SPEC = ServiceSpec(
    name="describe_topology_block",
    title="Describe Topology Block",
    summary="Return one bundled topology block manifest, design equations, and blueprint document.",
    phase="implemented",
    read_only=True,
)


def describe_topology_block(block_id: str) -> TopologyBlockDetail:
    """Return the manifest and blueprint for one bundled topology block."""

    manifest = load_topology_manifest(block_id)
    normalized_block_id = str(manifest["block_id"])
    document_name = str(manifest.get("document", "blueprint.md")).strip() or "blueprint.md"
    document_text = read_topology_document(normalized_block_id, document_name)
    raw_tags = manifest.get("tags", [])
    tags = tuple(str(tag).strip() for tag in raw_tags if str(tag).strip())
    reference = manifest.get("reference")
    return TopologyBlockDetail(
        block_id=normalized_block_id,
        title=str(manifest.get("title", normalized_block_id)),
        category=str(manifest.get("category", "")),
        summary=str(manifest.get("summary", "")),
        tags=tags,
        ports=_as_dict_tuple(manifest.get("ports")),
        parameters=_as_dict_tuple(manifest.get("parameters")),
        design_equations=_as_dict_tuple(manifest.get("design_equations")),
        control_notes=str(manifest.get("control_notes", "")),
        reference=dict(reference) if isinstance(reference, dict) else {},
        document_name=document_name,
        document=document_text,
        attribution=topology_attribution(),
    )


__all__ = ["SERVICE_SPEC", "TopologyBlockDetail", "describe_topology_block"]
