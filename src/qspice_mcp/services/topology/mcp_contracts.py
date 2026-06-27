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
        "description": "Lexical TF-IDF search over bundled topology blocks (id, title, summary, category, tags, control notes, ports, parameters, design equations, and blueprint text); returns matches ranked by cosine relevance.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Whitespace-separated keywords, for example 'step up rhp zero'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of ranked matches to return (default 10).",
                },
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
    "ingest_topology_contribution": {
        "title": "Ingest Topology Contribution",
        "description": "Validate a candidate topology-block manifest plus its blueprint document and stage them (manifest.json, blueprint, index_entry.json) into a sandboxed topology_contributions/<block_id>/ folder under the workspace for PR review. Does not modify the bundled knowledge pack.",
        "input_schema": {
            "type": "object",
            "required": ["manifest", "blueprint"],
            "properties": {
                "manifest": {
                    "type": "object",
                    "description": "Candidate topology-block manifest (same schema as validate_topology_contribution).",
                },
                "blueprint": {
                    "type": "string",
                    "description": "Clean-room blueprint document text; its file name must match manifest['document'].",
                },
                "output_dir": {
                    "type": "string",
                    "description": "Optional workspace-relative directory to stage under (defaults to the workspace root).",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Overwrite existing staged files for this block_id (default false).",
                },
            },
        },
    },
}
