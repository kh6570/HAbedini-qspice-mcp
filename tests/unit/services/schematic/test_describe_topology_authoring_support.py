"""Tests for describe_topology_authoring_support."""

from __future__ import annotations

from qspice_mcp.services.schematic.describe_topology_authoring_support import (
    describe_topology_authoring_support,
)


def test_describe_topology_authoring_support_lists_scratch_capabilities() -> None:
    result = describe_topology_authoring_support()

    capability_names = {entry.capability for entry in result.capabilities}
    assert "inductor" in capability_names
    assert "mosfet" in capability_names
    assert "junction" in capability_names
    assert "layout_suggestion" in capability_names
    assert "layout_spec" in capability_names
    assert "component_rotation" in capability_names
    assert "workspace_source_write" in capability_names
    assert result.scratch_buck_ready is True
    assert result.scratch_buck_instruction_id == "buck-converter-cpp"
    assert all(entry.supported for entry in result.capabilities)
    assert result.supported_component_kinds == (
        "behavioral",
        "capacitor",
        "diode",
        "ground",
        "inductor",
        "nmos",
        "pmos",
        "resistor",
        "voltage_source",
    )
