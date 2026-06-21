"""Static capability map for schematic topology authoring (creation intents)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from qspice_mcp.services._backends.schematic_editor_backend import (
    supported_simple_component_kinds,
)
from qspice_mcp.services.service_spec import ServiceSpec

TopologyCapabilityName = Literal[
    "blank_schematic",
    "simple_parts",
    "component_rotation",
    "inductor",
    "mosfet",
    "behavioral_source",
    "junction",
    "wire",
    "net_label",
    "dll_block",
    "workspace_source_write",
    "dll_build",
    "parameter",
    "analysis_instruction",
    "simulate",
    "waveform_readback",
    "layout_suggestion",
    "layout_spec",
]


@dataclass(frozen=True, slots=True)
class TopologyCapabilityEntry:
    """One topology authoring capability row."""

    capability: TopologyCapabilityName
    label: str
    tool: str | None
    supported: bool
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TopologyAuthoringSupport:
    """Machine-readable topology authoring capability map."""

    capabilities: tuple[TopologyCapabilityEntry, ...]
    supported_component_kinds: tuple[str, ...]
    scratch_buck_ready: bool
    scratch_buck_instruction_id: str
    notes: tuple[str, ...]


_CAPABILITY_CATALOG: tuple[TopologyCapabilityEntry, ...] = (
    TopologyCapabilityEntry(
        capability="blank_schematic",
        label="Create blank schematic",
        tool="create_schematic",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="simple_parts",
        label="Insert R/C/D/V/GND",
        tool="add_component",
        supported=True,
        limitations=(
            "Pass rotation_degrees in multiples of 45 at placement time.",
            "Use auto_place=true or suggest_component_placement to avoid overlapping parts.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="layout_suggestion",
        label="Suggest collision-free placement",
        tool="suggest_component_placement",
        supported=True,
        limitations=(
            "Uses conservative symbol footprints; verify dense layouts in the GUI.",
            "Complex buck layouts should still follow read_workflow_instruction coordinate tables.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="layout_spec",
        label="Batch placement from JSON layout spec",
        tool="apply_schematic_layout_spec",
        supported=True,
        limitations=(
            "Layout spec v1 covers component coordinates only (not wires, junctions, or labels).",
            "See describe_schematic_layout_spec for schema and bundled scratch_power_stage.v1.json.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="component_rotation",
        label="Rotate placed component",
        tool="set_component_rotation",
        supported=True,
        limitations=("Pin coordinates change with rotation; verify wires after rotating.",),
    ),
    TopologyCapabilityEntry(
        capability="inductor",
        label="Insert inductor (L)",
        tool="add_component",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="mosfet",
        label="Insert NMOS/PMOS library MOSFET",
        tool="add_component",
        supported=True,
        limitations=("Use component_kind nmos or pmos; value is the model name.",),
    ),
    TopologyCapabilityEntry(
        capability="behavioral_source",
        label="Insert behavioral voltage source (B)",
        tool="add_component",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="junction",
        label="Insert wire junction node",
        tool="add_junction",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="wire",
        label="Insert wire segment",
        tool="add_wire",
        supported=True,
        limitations=(
            "Large wire graphs are tedious; use read_workflow_instruction for coordinate tables.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="net_label",
        label="Insert net label",
        tool="add_net_label",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="dll_block",
        label="Insert multi-pin DLL block",
        tool="add_dll_block",
        supported=True,
        limitations=(
            "Pass full input_pin_names and output_pin_names lists; "
            "scaffold_dll_device_from_symbol emits TODO stubs only.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="workspace_source_write",
        label="Write workspace C/C++ source",
        tool="write_workspace_text_file",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="dll_build",
        label="Compile workspace DLL",
        tool="build_dll_device",
        supported=True,
        limitations=(
            "Auto mode prefers QSpice-bundled DMC (<install>/dm/bin/dmc.exe) when "
            "QSPICE_EXE is configured; C++98-era DMC limits apply — use toolchain=msvc "
            "for modern C++.",
        ),
    ),
    TopologyCapabilityEntry(
        capability="parameter",
        label="Set schematic .param",
        tool="set_parameter",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="analysis_instruction",
        label="Add analysis instruction",
        tool="add_instruction",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="simulate",
        label="Run simulation",
        tool="run_simulation",
        supported=True,
    ),
    TopologyCapabilityEntry(
        capability="waveform_readback",
        label="Read/plot waveforms",
        tool="plot_waveforms",
        supported=True,
    ),
)


SERVICE_SPEC = ServiceSpec(
    name="describe_topology_authoring_support",
    title="Describe Topology Authoring Support",
    summary=(
        "Return a static machine-readable map of schematic creation capabilities "
        "for scratch topology authoring (Track A)."
    ),
    phase="implemented",
    read_only=True,
)


def describe_topology_authoring_support() -> TopologyAuthoringSupport:
    """Return the static topology authoring capability map."""

    scratch_ready = all(entry.supported for entry in _CAPABILITY_CATALOG)
    return TopologyAuthoringSupport(
        capabilities=_CAPABILITY_CATALOG,
        supported_component_kinds=supported_simple_component_kinds(),
        scratch_buck_ready=scratch_ready,
        scratch_buck_instruction_id="buck-converter-cpp",
        notes=(
            "Track A scratch buck: read_workflow_instruction(instruction_id=buck-converter-cpp); "
            "do not use materialize_reference_circuit.",
            "Track B catalog: materialize_reference_circuit(recipe_id=buck_converter_cpp).",
            "Readable placement: call suggest_component_placement before add_component, "
            "or pass auto_place=true on add_component.",
            "Batch placement: write a v1 JSON layout spec and call apply_schematic_layout_spec.",
        ),
    )


__all__ = [
    "SERVICE_SPEC",
    "TopologyAuthoringSupport",
    "TopologyCapabilityEntry",
    "TopologyCapabilityName",
    "describe_topology_authoring_support",
]
