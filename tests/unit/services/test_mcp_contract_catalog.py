"""Tests for service-package MCP contract discovery."""

from __future__ import annotations

from qspice_mcp.mcp.tool_registry import (
    _DESCRIBE_SERVER_CAPABILITIES_SERVICE,
    build_runtime_tool_registry,
    build_tool_registry,
)
from qspice_mcp.services._internals.service_catalog import build_service_spec_catalog


def test_enriched_service_specs_expose_input_schema_for_implemented_tools() -> None:
    specs = build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))
    implemented = [spec for spec in specs if spec.phase == "implemented"]

    assert implemented
    assert all(spec.input_schema is not None for spec in implemented)
    assert all(spec.description for spec in implemented)


def test_mcp_contract_catalog_matches_runtime_tool_registry() -> None:
    registry_names = {tool.name for tool in build_runtime_tool_registry(build_tool_registry())}
    spec_names = {
        spec.name
        for spec in build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))
        if spec.phase == "implemented"
    }

    assert registry_names == spec_names
