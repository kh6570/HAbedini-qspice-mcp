"""Server tool metadata."""

from __future__ import annotations

from .common import _ann

SERVER_TOOL_METADATA: dict[str, dict[str, object]] = {
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
}


__all__ = ["SERVER_TOOL_METADATA"]
