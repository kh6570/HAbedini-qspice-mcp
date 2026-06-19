"""Tests for MCP progress bridge helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.infra.progress import ProgressBridge, progress_scope, report_progress


class _FakeContext:
    def __init__(self) -> None:
        self.events: list[tuple[float, float | None, str | None]] = []

    async def report_progress(
        self,
        progress: float,
        *,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        self.events.append((progress, total, message))


@pytest.mark.anyio
async def test_progress_bridge_reports_through_context() -> None:
    context = _FakeContext()
    bridge = ProgressBridge(context)

    await bridge._report_async(2.0, 5.0, "running")

    assert context.events == [(2.0, 5.0, "running")]


def test_report_progress_is_noop_without_bound_context() -> None:
    report_progress(1.0, total=2.0, message="noop")


def test_progress_scope_resets_context() -> None:
    with progress_scope(None):
        report_progress(0.5, total=1.0)
    report_progress(1.0, total=1.0)


def test_progress_bridge_report_swallows_missing_async_portal() -> None:
    bridge = ProgressBridge(_FakeContext())
    bridge.report(1.0, total=2.0, message="outside-request")


def test_bind_context_accepts_fastmcp_context_shape() -> None:
    from qspice_mcp.infra.progress import bind_context, reset_context

    token = bind_context(_FakeContext())
    try:
        report_progress(1.0, total=1.0, message="bound")
    finally:
        reset_context(token)
