"""Tests for bundled MCP prompt definitions."""

from __future__ import annotations

from qspice_mcp.mcp.prompts import get_prompt_definitions, render_prompt_message


def test_get_prompt_definitions_returns_registered_workflows() -> None:
    definitions = get_prompt_definitions()
    names = {definition.name for definition in definitions}
    assert names == {
        "qspice_author_dll_device",
        "qspice_buck_converter_from_scratch",
        "qspice_debug_convergence",
        "qspice_run_and_measure",
        "qspice_smps_loop_gain",
        "qspice_sweep_design",
        "qspice_tolerance_analysis",
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


def test_render_tolerance_analysis_prompt_covers_mc_and_worst_case() -> None:
    message = render_prompt_message(
        "qspice_tolerance_analysis",
        schematic_path="reg.qsch",
        metric="V(ref)",
        runs="100",
    )
    assert "reg.qsch" in message
    assert "V(ref)" in message
    assert "100" in message
    assert "prepare_monte_carlo" in message
    assert "prepare_worst_case" in message
    assert "summarize_tolerance_analysis" in message


def test_render_author_dll_device_prompt_prefers_device_spec_path() -> None:
    message = render_prompt_message("qspice_author_dll_device", device_kind="mcu")
    assert "describe_device_spec" in message
    assert "create_dll_device_from_spec" in message
    assert "scaffold_dll_device_from_symbol" in message


def test_render_smps_loop_gain_prompt_covers_bode_and_fra() -> None:
    message = render_prompt_message(
        "qspice_smps_loop_gain",
        schematic_path="smps.qsch",
        perturbation_source="V5",
        settling_time="3m",
    )
    assert "smps.qsch" in message
    assert "V5" in message
    assert "3m" in message
    assert "prepare_bode_analysis" in message
    assert "measure_stability_margins" in message
    assert "fra" in message
