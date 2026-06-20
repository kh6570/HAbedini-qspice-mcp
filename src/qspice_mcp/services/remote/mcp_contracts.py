"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "submit_remote_simulation": {
        "title": "Submit Remote Simulation",
        "description": "Submit one remote-style simulation session for background execution.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_dir": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "poll_remote_run": {
        "title": "Poll Remote Run",
        "description": "Read live status for one submitted remote-style session.",
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {"session_id": {"type": "string"}},
        },
    },
    "download_remote_artifacts": {
        "title": "Download Remote Artifacts",
        "description": "Package selected remote-style session artifacts into one zip bundle.",
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
                "output_path": {"type": "string"},
                "artifact_kinds": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "string",
                        "enum": ["summary", "source", "netlist", "log", "raw"],
                    },
                },
            },
        },
    },
    "close_remote_session": {
        "title": "Close Remote Session",
        "description": "Close one remote-style session and optionally delete its zip bundle.",
        "input_schema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {"session_id": {"type": "string"}, "delete_bundle": {"type": "boolean"}},
        },
    },
}
