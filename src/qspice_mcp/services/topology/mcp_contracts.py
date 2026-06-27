"""MCP input schemas and descriptions for the topology knowledge-pack package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "list_topology_blocks": {
        "title": "List Topology Blocks",
        "description": "List bundled composable DC-DC converter topology blocks (id, title, category, tags, summary) plus the knowledge-pack attribution.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "describe_topology_block": {
        "title": "Describe Topology Block",
        "description": "Return one bundled topology block manifest (ports, parameters, design equations, control notes, reference) and its clean-room blueprint document.",
        "input_schema": {
            "type": "object",
            "required": ["block_id"],
            "properties": {
                "block_id": {
                    "type": "string",
                    "description": "Topology block id, for example 'buck_converter'.",
                }
            },
        },
    },
    "search_topology_blocks": {
        "title": "Search Topology Blocks",
        "description": "Keyword-search bundled topology blocks by id, title, summary, category, and tags; returns ranked matches.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Whitespace-separated keywords, for example 'step up rhp'.",
                }
            },
        },
    },
    "validate_topology_contribution": {
        "title": "Validate Topology Contribution",
        "description": "Validate a candidate topology-block manifest object against the knowledge-pack schema and report errors and warnings.",
        "input_schema": {
            "type": "object",
            "required": ["manifest"],
            "properties": {
                "manifest": {
                    "type": "object",
                    "description": "Candidate topology-block manifest to validate.",
                }
            },
        },
    },
}
