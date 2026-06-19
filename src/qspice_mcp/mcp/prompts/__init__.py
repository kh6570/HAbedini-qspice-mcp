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
    )


def _buck_converter_prompt(vin: str = "12", vout: str = "5", iout: str = "1") -> str:
    return (
        "Build a buck converter from scratch in the QSpice workspace using MCP tools only.\n\n"
        f"Targets: Vin={vin} V, Vout={vout} V, Iout={iout} A.\n\n"
        "Workflow:\n"
        "1. Call describe_topology_authoring_support and describe_server_capabilities.\n"
        "2. Optionally list_reference_circuit_recipes then describe_reference_circuit_recipe "
        "for buck_converter_cpp before authoring.\n"
        "3. create_schematic or use materialize_reference_circuit only if a recipe is chosen.\n"
        "4. Author the power stage with add_component, add_wire, add_junction, add_net_label.\n"
        "5. add_instruction or prepare_transient for `.tran`, then generate_netlist.\n"
        "6. run_simulation(dry_run=True) then run_simulation on the derived netlist.\n"
        "7. list_signals and read_waveform / measure_waveform on V(out) and switch nodes.\n"
        "Keep netlists derived; treat `.qsch` as source of truth."
    )


def _debug_convergence_prompt(log_path: str) -> str:
    return (
        "Diagnose why this QSpice simulation failed to converge.\n\n"
        f"Log path: {log_path}\n\n"
        "Workflow:\n"
        "1. read_log on the log path (include tail + error sections).\n"
        "2. inspect_schematic if the source is `.qsch`; otherwise read the netlist sidecar.\n"
        "3. Classify: missing model/GND, timestep, initial condition, or device-specific issue.\n"
        "4. Apply the smallest schematic/netlist fix and re-run with dry_run then full sim.\n"
        "5. Report the root cause, fix applied, and whether the rerun succeeded."
    )


def _run_and_measure_prompt(schematic_path: str, signals: str = "V(out)") -> str:
    return (
        "Simulate this circuit and return bounded measurements.\n\n"
        f"Schematic/source: {schematic_path}\n"
        f"Signals: {signals}\n\n"
        "Workflow:\n"
        "1. generate_netlist if the source is `.qsch`.\n"
        "2. run_simulation on the derived `.net`/`.cir`.\n"
        "3. list_signals, then read_waveform with budgets respected.\n"
        "4. measure_waveform for min/max/RMS on requested signals.\n"
        "5. Summarize pass/fail against expected operating point or ripple targets."
    )


def _author_dll_device_prompt(device_kind: str = "control") -> str:
    return (
        "Author a mixed-signal DLL/C-block device for QSpice.\n\n"
        f"Device kind: {device_kind}\n\n"
        "Workflow:\n"
        "1. describe_mixed_signal_support and describe_server_capabilities.\n"
        "2. scaffold_dll_device or scaffold_dll_device_from_symbol as appropriate.\n"
        "3. write_workspace_text_file for C/C++ source; build_dll_device when MSVC/DMC is available.\n"
        "4. add_dll_block / add_dll_block_pin on the schematic; validate_dll_symbol_signature.\n"
        "5. generate_netlist with QUX fallback if needed, then run_simulation smoke test."
    )


def _sweep_design_prompt(schematic_path: str, param: str, sweep_range: str) -> str:
    return (
        "Sweep one design parameter and summarize the batch results.\n\n"
        f"Schematic: {schematic_path}\n"
        f"Parameter: {param}\n"
        f"Range: {sweep_range}\n\n"
        "Workflow:\n"
        "1. Confirm `.qsch` source; generate_netlist if stale.\n"
        "2. Choose run_value_sweep, run_param_sweep, or run_model_sweep matching the parameter kind.\n"
        "3. Use parallelism=1 unless the workspace is isolated per run.\n"
        "4. summarize_batch / collect_batch_results; read key waveforms for corner runs only.\n"
        "5. Report optimal value and any constraint violations."
    )


_PROMPT_BUILDERS: dict[str, Callable[..., str]] = {
    "qspice_buck_converter_from_scratch": _buck_converter_prompt,
    "qspice_debug_convergence": _debug_convergence_prompt,
    "qspice_run_and_measure": _run_and_measure_prompt,
    "qspice_author_dll_device": _author_dll_device_prompt,
    "qspice_sweep_design": _sweep_design_prompt,
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
