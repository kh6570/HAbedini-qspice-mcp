# In the name of God, the Most Gracious, the Most Merciful
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
    assert "qspice-getting-started" in message
    assert "sweep.md" in message
    assert "buck.qsch" in message
    assert "L1" in message
    assert "1u:10u:1u" in message


def test_render_tolerance_analysis_prompt_names_the_skill() -> None:
    message = render_prompt_message(
        "qspice_tolerance_analysis",
        schematic_path="reg.qsch",
        metric="V(ref)",
        runs="100",
    )
    assert "qspice-getting-started" in message
    assert "tolerance.md" in message
    assert "reg.qsch" in message
    assert "V(ref)" in message
    assert "100" in message


def test_render_author_dll_device_prompt_names_the_skill() -> None:
    message = render_prompt_message("qspice_author_dll_device", device_kind="mcu")
    assert "qspice-mixed-signal-dll" in message
    assert "workflow.md" in message
    assert "mcu" in message


def test_render_smps_loop_gain_prompt_names_the_skill() -> None:
    message = render_prompt_message(
        "qspice_smps_loop_gain",
        schematic_path="smps.qsch",
        perturbation_source="V5",
        settling_time="3m",
    )
    assert "qspice-power-electronics" in message
    assert "loop-gain.md" in message
    assert "smps.qsch" in message
    assert "V5" in message
    assert "3m" in message


def test_prompt_bodies_do_not_restate_numbered_workflows() -> None:
    samples: dict[str, dict[str, str]] = {
        "qspice_author_dll_device": {},
        "qspice_buck_converter_from_scratch": {},
        "qspice_debug_convergence": {"log_path": "run.log"},
        "qspice_run_and_measure": {"schematic_path": "a.qsch"},
        "qspice_smps_loop_gain": {"schematic_path": "a.qsch"},
        "qspice_sweep_design": {
            "schematic_path": "a.qsch",
            "param": "L1",
            "sweep_range": "1u:2u",
        },
        "qspice_tolerance_analysis": {"schematic_path": "a.qsch"},
    }
    for name, arguments in samples.items():
        message = render_prompt_message(name, **arguments)
        assert "qspice-" in message
        assert "\n1. " not in message
