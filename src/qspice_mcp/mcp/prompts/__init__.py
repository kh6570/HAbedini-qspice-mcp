# In the name of God, the Most Gracious, the Most Merciful
"""MCP prompt metadata and workflow message builders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class PromptDefinition:
    """Metadata for one MCP prompt exposed by the server."""

    name: str
    title: str
    description: str


def get_prompt_definitions() -> tuple[PromptDefinition, ...]:
    """Return registered MCP prompt definitions."""

    return (
        PromptDefinition(
            name="qspice_buck_converter_from_scratch",
            title="Buck Converter From Scratch",
            description=(
                "Guide authoring a buck converter schematic, generating a netlist, "
                "and running a transient simulation."
            ),
        ),
        PromptDefinition(
            name="qspice_debug_convergence",
            title="Debug Convergence",
            description="Structured workflow for diagnosing a non-converging QSpice simulation.",
        ),
        PromptDefinition(
            name="qspice_run_and_measure",
            title="Run And Measure",
            description="Run a simulation and read bounded waveform measurements for key signals.",
        ),
        PromptDefinition(
            name="qspice_author_dll_device",
            title="Author DLL Device",
            description="Scaffold and build a mixed-signal C-block/DLL device for QSpice.",
        ),
        PromptDefinition(
            name="qspice_sweep_design",
            title="Sweep Design Parameter",
            description="Plan and execute a parameter sweep on an existing schematic.",
        ),
        PromptDefinition(
            name="qspice_smps_loop_gain",
            title="SMPS Loop Gain",
            description=(
                "Extract closed-loop SMPS frequency response with `.bode`, measure "
                "stability margins, and verify crossover points with `.meas fra`."
            ),
        ),
        PromptDefinition(
            name="qspice_tolerance_analysis",
            title="Tolerance Analysis",
            description=(
                "Quantify how component tolerances affect a design metric via "
                "Monte Carlo and worst-case runs, then summarize the spread."
            ),
        ),
    )


def _buck_converter_prompt(vin: str = "12", vout: str = "5", iout: str = "1") -> str:
    return (
        "Follow the qspice-power-electronics skill and open reference/buck-from-scratch.md.\n\n"
        f"Vin: {vin} V\n"
        f"Vout: {vout} V\n"
        f"Iout: {iout} A\n"
    )


def _debug_convergence_prompt(log_path: str) -> str:
    return (
        "Follow the qspice-convergence-debugging skill and open reference/workflow.md.\n\n"
        f"Log path: {log_path}\n"
    )


def _run_and_measure_prompt(schematic_path: str, signals: str = "V(out)") -> str:
    return (
        "Follow the qspice-getting-started skill and open reference/simulate-and-read.md.\n\n"
        f"Schematic: {schematic_path}\n"
        f"Signals: {signals}\n"
    )


def _author_dll_device_prompt(device_kind: str = "control") -> str:
    return (
        "Follow the qspice-mixed-signal-dll skill and open reference/workflow.md.\n\n"
        f"Device kind: {device_kind}\n"
    )


def _sweep_design_prompt(schematic_path: str, param: str, sweep_range: str) -> str:
    return (
        "Follow the qspice-getting-started skill and open reference/sweep.md.\n\n"
        f"Schematic: {schematic_path}\n"
        f"Parameter: {param}\n"
        f"Range: {sweep_range}\n"
    )


def _smps_loop_gain_prompt(
    schematic_path: str,
    perturbation_source: str = "Vinj",
    settling_time: str = "2m",
) -> str:
    return (
        "Follow the qspice-power-electronics skill and open reference/loop-gain.md.\n\n"
        f"Schematic: {schematic_path}\n"
        f"Perturbation source: {perturbation_source}\n"
        f"Settling time: {settling_time}\n"
    )


def _tolerance_analysis_prompt(
    schematic_path: str,
    metric: str = "V(out)",
    runs: str = "50",
) -> str:
    return (
        "Follow the qspice-getting-started skill and open reference/tolerance.md.\n\n"
        f"Schematic: {schematic_path}\n"
        f"Metric: {metric}\n"
        f"Monte Carlo runs: {runs}\n"
    )


_PROMPT_BUILDERS: dict[str, Callable[..., str]] = {
    "qspice_buck_converter_from_scratch": _buck_converter_prompt,
    "qspice_debug_convergence": _debug_convergence_prompt,
    "qspice_run_and_measure": _run_and_measure_prompt,
    "qspice_author_dll_device": _author_dll_device_prompt,
    "qspice_sweep_design": _sweep_design_prompt,
    "qspice_smps_loop_gain": _smps_loop_gain_prompt,
    "qspice_tolerance_analysis": _tolerance_analysis_prompt,
}


def render_prompt_message(name: str, **arguments: str) -> str:
    """Render one prompt body from registered builders."""

    builder = _PROMPT_BUILDERS.get(name)
    if builder is None:
        raise KeyError(f"Unknown prompt: {name}")
    return builder(**arguments)


__all__ = [
    "PromptDefinition",
    "get_prompt_definitions",
    "render_prompt_message",
]
