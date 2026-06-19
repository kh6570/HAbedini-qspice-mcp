"""Tests for bundled MCP prompt definitions."""

from __future__ import annotations

from qspice_mcp.mcp.prompts import get_prompt_definitions, render_prompt_message


def test_get_prompt_definitions_returns_five_workflows() -> None:
    definitions = get_prompt_definitions()
    names = {definition.name for definition in definitions}
    assert names == {
        "qspice_author_dll_device",
        "qspice_buck_converter_from_scratch",
        "qspice_debug_convergence",
        "qspice_run_and_measure",
        "qspice_sweep_design",
    }


def test_render_prompt_message_includes_arguments() -> None:
    message = render_prompt_message(
        "qspice_sweep_design",
        schematic_path="buck.qsch",
        param="L1",
        sweep_range="1u:10u:1u",
    )
    assert "buck.qsch" in message
    assert "L1" in message
    assert "1u:10u:1u" in message
