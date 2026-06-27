"""Server-level introspection tool handlers."""

from __future__ import annotations

from qspice_mcp.mcp.capabilities import (
    describe_server_capabilities as describe_server_capabilities_runtime,
)

__all__ = ["describe_server_capabilities_runtime"]
