"""Tests for ServiceSpec-driven MCP tool annotation resolution."""

from __future__ import annotations

from qspice_mcp.mcp.tool_registry import resolve_tool_annotations
from qspice_mcp.services.service_spec import ServiceSpec


def test_resolve_tool_annotations_uses_service_read_only_flag() -> None:
    spec = ServiceSpec(
        name="list_signals",
        title="List Signals",
        summary="List signals.",
        phase="implemented",
        read_only=True,
    )

    resolved = resolve_tool_annotations(spec, {"annotations": {"read_only_hint": False}})

    assert resolved.read_only_hint is True


def test_resolve_tool_annotations_sets_open_world_for_long_running_tools() -> None:
    spec = ServiceSpec(
        name="run_simulation",
        title="Run Simulation",
        summary="Run simulation.",
        phase="implemented",
        read_only=False,
        long_running=True,
    )

    resolved = resolve_tool_annotations(spec, {"annotations": {}})

    assert resolved.open_world_hint is True


def test_resolve_tool_annotations_uses_service_destructive_and_idempotent_defaults() -> None:
    destructive = ServiceSpec(
        name="remove_component",
        title="Remove Component",
        summary="Remove one component.",
        phase="implemented",
        read_only=False,
        destructive=True,
    )
    idempotent_write = ServiceSpec(
        name="generate_netlist",
        title="Generate Netlist",
        summary="Generate netlist.",
        phase="implemented",
        read_only=False,
        idempotent=True,
    )

    assert resolve_tool_annotations(destructive, {"annotations": {}}).destructive_hint is True
    assert resolve_tool_annotations(idempotent_write, {"annotations": {}}).idempotent_hint is True
    assert resolve_tool_annotations(idempotent_write, {"annotations": {}}).read_only_hint is False
