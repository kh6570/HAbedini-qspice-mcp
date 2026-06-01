"""Tests for the tool registry and schema derivation."""

from __future__ import annotations

from qspice_mcp.mcp.tool_registry import (
    ToolAnnotations,
    ToolDefinition,
    build_runtime_tool_registry,
    build_tool_registry,
)
from qspice_mcp.services import get_service_specs


class TestToolAnnotations:
    def test_defaults_are_false(self) -> None:
        ann = ToolAnnotations()
        assert ann.read_only_hint is False
        assert ann.destructive_hint is False
        assert ann.idempotent_hint is False
        assert ann.open_world_hint is False

    def test_explicit_values(self) -> None:
        ann = ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        )
        assert ann.read_only_hint is True
        assert ann.idempotent_hint is True


class TestToolDefinition:
    def test_summary_shape(self) -> None:
        td = ToolDefinition(
            name="test_tool",
            title="Test Tool",
            description="A test.",
            input_schema={"type": "object"},
            annotations=ToolAnnotations(read_only_hint=True),
            service=get_service_specs()[0],
        )
        s = td.summary()
        assert s["name"] == "test_tool"
        assert s["title"] == "Test Tool"
        assert s["read_only"] is True


class TestBuildToolRegistry:
    def test_matches_service_catalog_count(self) -> None:
        specs = get_service_specs()
        tools = build_tool_registry(specs)
        assert len(tools) == len(specs)

    def test_tool_order_matches_spec_order(self) -> None:
        specs = get_service_specs()
        tools = build_tool_registry(specs)
        assert tuple(t.name for t in tools) == tuple(s.name for s in specs)

    def test_all_tools_have_input_schema(self) -> None:
        tools = build_tool_registry()
        for tool in tools:
            assert "type" in tool.input_schema
            assert "required" in tool.input_schema or "properties" in tool.input_schema

    def test_all_tools_have_annotations(self) -> None:
        tools = build_tool_registry()
        for tool in tools:
            assert isinstance(tool.annotations, ToolAnnotations)
            assert isinstance(tool.annotations.read_only_hint, bool)

    def test_all_tools_have_non_empty_description(self) -> None:
        tools = build_tool_registry()
        for tool in tools:
            assert len(tool.description) > 0
            assert len(tool.title) > 0


class TestBuildRuntimeToolRegistry:
    def test_filters_out_planned(self) -> None:
        tools = build_tool_registry()
        runtime = build_runtime_tool_registry(tools)
        assert len(runtime) <= len(tools)
        assert all(t.service.phase == "implemented" for t in runtime)

    def test_all_runtime_tools_in_planned(self) -> None:
        tools = build_tool_registry()
        runtime = build_runtime_tool_registry(tools)
        runtime_names = {t.name for t in runtime}
        for tool in tools:
            if tool.service.phase == "implemented":
                assert tool.name in runtime_names
