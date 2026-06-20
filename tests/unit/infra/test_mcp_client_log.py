"""Tests for MCP client log mirroring."""

from __future__ import annotations

import pytest

from qspice_mcp.infra.mcp_client_log import (
    _emit_async,
    bind_mcp_client_log_context,
    mcp_client_log_processor,
    mirror_client_log,
    reset_mcp_client_log_context,
)


class _RecordingContext:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    async def info(self, message: str) -> None:
        self.messages.append(("info", message))


def test_mirror_client_log_is_noop_without_bound_context() -> None:
    mirror_client_log("info", "noop")


def test_mcp_client_log_processor_ignores_untracked_events() -> None:
    event = mcp_client_log_processor(None, "info", {"event": "other"})
    assert event["event"] == "other"


def test_mcp_client_log_processor_formats_structured_tool_event() -> None:
    event = mcp_client_log_processor(
        None,
        "info",
        {
            "event": "tool_request_completed",
            "tool": "run_simulation",
            "component": "mcp.tool",
            "duration_s": 0.25,
            "read_only": False,
        },
    )
    assert event["tool"] == "run_simulation"


@pytest.mark.anyio
async def test_emit_async_records_context_message() -> None:
    context = _RecordingContext()
    await _emit_async(context, "info", "hello")
    assert context.messages == [("info", "hello")]


def test_mirror_client_log_swallows_missing_async_portal() -> None:
    context = _RecordingContext()
    token = bind_mcp_client_log_context(context)
    try:
        mirror_client_log("info", "hello")
    finally:
        reset_mcp_client_log_context(token)
