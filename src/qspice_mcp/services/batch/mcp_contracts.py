"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

from qspice_mcp.services._internals.mcp_schema_common import (
    _RETAINED_ARTIFACT_POLICY,
    _SCALAR_VALUE,
    _STEP_FILTER_VALUE,
)

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "submit_batch": {
        "title": "Submit Batch",
        "description": "Submit a background value, parameter, or model sweep batch.",
        "input_schema": {
            "type": "object",
            "required": ["batch_kind", "source_path"],
            "properties": {
                "batch_kind": {"type": "string", "enum": ["component_value", "parameter", "model"]},
                "source_path": {"type": "string"},
                "reference": {"type": "string"},
                "values": {"type": "array", "items": _SCALAR_VALUE, "minItems": 1},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "array",
                        "minItems": 1,
                        "items": _STEP_FILTER_VALUE,
                    },
                },
                "models": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
    },
    "get_batch_status": {
        "title": "Get Batch Status",
        "description": "Read live status for one submitted batch.",
        "input_schema": {
            "type": "object",
            "required": ["batch_id"],
            "properties": {"batch_id": {"type": "string"}},
        },
    },
    "collect_batch_results": {
        "title": "Collect Batch Results",
        "description": "Return completed batch results when available.",
        "input_schema": {
            "type": "object",
            "required": ["batch_id"],
            "properties": {"batch_id": {"type": "string"}},
        },
    },
    "cancel_batch": {
        "title": "Cancel Batch",
        "description": "Request cancellation for one submitted batch.",
        "input_schema": {
            "type": "object",
            "required": ["batch_id"],
            "properties": {"batch_id": {"type": "string"}},
        },
    },
}
