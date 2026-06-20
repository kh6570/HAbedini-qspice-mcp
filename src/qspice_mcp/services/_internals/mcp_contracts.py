"""MCP contracts for services without a dedicated package module."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "describe_server_capabilities": {
        "title": "Describe Server Capabilities",
        "description": (
            "Report server-level backend availability, degraded tool groups, "
            "and feature flags for the current runtime."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
}
