"""Server-level capability summary helpers for MCP clients."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from qspice_mcp.adapters import describe_adapters, probe_qspice, select_adapter
from qspice_mcp.core.error_taxonomy import describe_error_taxonomy
from qspice_mcp.core.exceptions import AdapterNotFoundError
from qspice_mcp.infra.telemetry import describe_telemetry_state
from qspice_mcp.mcp.definition import build_server_definition
from qspice_mcp.mcp.prompts import get_prompt_definitions
from qspice_mcp.mcp.resources import get_resource_definitions
from qspice_mcp.mcp.resources.registration import reference_document_names
from qspice_mcp.services._backends.schematic_editor import load_qsch_editor_factory
from qspice_mcp.services._backends.waveform import _load_rawread_factory
from qspice_mcp.services.artifacts._raw_write import load_rawwrite_api
from qspice_mcp.services.artifacts.describe_qux_export_support import (
    describe_qux_export_support,
)
from qspice_mcp.services.mixed_signal._dll_toolchain_probe import describe_dll_build_toolchain

if TYPE_CHECKING:
    from qspice_mcp.adapters.probe import ProbeResult
    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.mcp.tool_registry import ToolDefinition

_SIMULATION_EXECUTION_TOOLS = frozenset(
    {
        "run_simulation",
        "run_value_sweep",
        "run_param_sweep",
        "run_monte_carlo",
        "run_worst_case",
        "run_model_sweep",
        "submit_batch",
        "submit_remote_simulation",
    }
)
_WAVEFORM_ACCESS_TOOLS = frozenset(
    {
        "list_steps",
        "list_signals",
        "read_waveform",
        "measure_waveform",
        "measure_bode_response",
        "measure_stability_margins",
        "measure_step_response",
        "measure_efficiency",
        "compute_thd",
        "export_fft_spectrum",
        "plot_waveforms",
        "read_device_operating_points",
        "filter_device_operating_points",
        "summarize_device_operating_points",
        "read_measures",
        "list_measures",
        "read_log",
        "read_fourier",
        "read_noise",
        "export_derived_raw",
        "merge_waveforms",
        "compare_waveforms",
    }
)
_COMPANION_EXPORT_TOOLS = frozenset(
    {
        "describe_qux_export_support",
        "export_waveform_ascii",
        "export_waveform_csv",
        "export_waveform_spice",
        "export_touchstone_s2p",
        "generate_dll_variables",
    }
)
_EXTENDED_RAW_EXPORT_TOOLS = frozenset({"export_derived_raw", "merge_waveforms"})
_LIVE_GUI_TOOLS = frozenset(
    {
        "describe_live_gui_support",
        "scaffold_live_gui_session",
        "launch_live_gui_session",
        "poll_live_gui_session",
        "send_live_gui_session_command",
        "poll_live_gui_session_events",
        "close_live_gui_session",
    }
)

_SCHEMATIC_EDITING_TOOLS = frozenset(
    {
        "add_component",
        "add_component_from_qsym",
        "add_component_symbol_drawing",
        "add_dll_block",
        "add_dll_block_pin",
        "add_instruction",
        "add_junction",
        "add_library_component",
        "add_net_label",
        "add_wire",
        "apply_schematic_layout_spec",
        "check_schematic",
        "create_schematic",
        "create_starter_schematic",
        "describe_edit_capability",
        "describe_schematic_edit_support",
        "describe_schematic_layout_spec",
        "export_symbol_to_qsym",
        "inspect_schematic",
        "import_circuit_bundle",
        "list_components",
        "materialize_reference_circuit",
        "normalize_component_text_rotation",
        "read_component",
        "read_component_symbol",
        "remove_component",
        "remove_component_symbol_drawing",
        "remove_dll_block_pin",
        "remove_instruction",
        "remove_junction",
        "remove_net_label",
        "remove_wire",
        "rename_component_reference",
        "render_schematic_image",
        "save_schematic_as",
        "set_component_parameters",
        "set_component_position",
        "set_component_symbol_drawing",
        "set_component_symbol_pin",
        "set_component_symbol_text",
        "set_component_value",
        "set_dll_block_pin_role",
        "set_element_model",
        "set_parameter",
        "suggest_component_placement",
    }
)
_TOPOLOGY_AUTHORING_TOOLS = frozenset(
    {
        "describe_topology_authoring_support",
        "list_workflow_instructions",
        "read_workflow_instruction",
        "write_workspace_text_file",
        "list_reference_circuit_recipes",
        "describe_reference_circuit_recipe",
        "describe_device_spec",
        "create_dll_device_from_spec",
        "build_dll_device",
    }
)
_TOPOLOGY_KNOWLEDGE_TOOLS = frozenset(
    {
        "list_topology_blocks",
        "describe_topology_block",
        "search_topology_blocks",
        "validate_topology_contribution",
        "ingest_topology_contribution",
    }
)


def _guidance_summary() -> dict[str, object]:
    """Advertise the non-tool surfaces: prompts, resources, and installable skills."""

    return {
        "prompts": [
            {
                "name": definition.name,
                "title": definition.title,
                "description": definition.description,
            }
            for definition in get_prompt_definitions()
        ],
        "resources": {
            "static": [definition.uri for definition in get_resource_definitions()],
            "templates": [
                "reference://{document}",
                "recipe://{recipe_id}/manifest",
                "recipe://{recipe_id}/schematic",
                "recipe://{recipe_id}/{document}",
                "workspace-artifact://{relpath}",
            ],
            "reference_documents": list(reference_document_names()),
        },
        "skills": {
            "description": (
                "Bundled agent skills (client-side guidance, not MCP tools) ship in "
                "the qspice_mcp package under data/skills/."
            ),
            "groups": ["qspice-core"],
            "install_hint": (
                "pwsh -File scripts/install_skills.ps1 "
                "(copies skills into ~/.agents/skills/ by default)"
            ),
        },
    }


def _selected_adapter_summary(probe: ProbeResult) -> dict[str, object] | None:
    try:
        return select_adapter(probe).describe(probe).summary()
    except AdapterNotFoundError:
        return None


def _tool_names(tools: tuple[ToolDefinition, ...]) -> frozenset[str]:
    return frozenset(tool.name for tool in tools)


def _supported_tools(
    available_tools: frozenset[str],
    candidates: frozenset[str],
) -> tuple[str, ...]:
    return tuple(name for name in sorted(candidates) if name in available_tools)


def _group_summary(
    *,
    name: str,
    title: str,
    state: str,
    tools: tuple[str, ...],
    reason: str | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "title": title,
        "state": state,
        "tool_count": len(tools),
        "tools": list(tools),
        "reason": reason,
    }


def _build_tool_groups(
    *,
    tools: tuple[ToolDefinition, ...],
    probe: ProbeResult,
    selected_adapter: dict[str, object] | None,
    rawread_backend: str | None,
    rawwrite_backend: str | None,
    qsch_editor_backend: str | None,
    qux_available: bool,
    qux_reason: str | None,
    settings: QSpiceSettings,
) -> tuple[dict[str, object], ...]:
    available_tools = _tool_names(tools)
    groups: list[dict[str, object]] = []

    simulation_tools = _supported_tools(available_tools, _SIMULATION_EXECUTION_TOOLS)
    if simulation_tools:
        groups.append(
            _group_summary(
                name="simulation_execution",
                title="Simulation Execution",
                state="healthy" if probe.exists and selected_adapter is not None else "degraded",
                tools=simulation_tools,
                reason=(
                    None
                    if probe.exists and selected_adapter is not None
                    else (
                        "No compatible local QSpice executable is available for "
                        "CLI-backed simulation tools."
                    )
                ),
            )
        )

    waveform_tools = _supported_tools(available_tools, _WAVEFORM_ACCESS_TOOLS)
    if waveform_tools:
        groups.append(
            _group_summary(
                name="waveform_access",
                title="Waveform Access",
                state="healthy" if rawread_backend is not None else "partial",
                tools=waveform_tools,
                reason=(
                    None
                    if rawread_backend is not None
                    else (
                        "No compatible RawRead backend is installed. Common read-only "
                        "signal, step, waveform, Bode, THD, FFT, and operating-point "
                        "inspection still works for the repo-owned clean-room raw format "
                        "plus the supported external compatibility slices, but broader "
                        "`.qraw` dialect coverage remains unavailable."
                    )
                ),
            )
        )

    schematic_edit_tools = _supported_tools(available_tools, _SCHEMATIC_EDITING_TOOLS)
    if schematic_edit_tools:
        groups.append(
            _group_summary(
                name="schematic_editing",
                title="Schematic Editing",
                state="healthy" if qsch_editor_backend is not None else "degraded",
                tools=schematic_edit_tools,
                reason=(
                    None
                    if qsch_editor_backend is not None
                    else (
                        "No compatible QschEditor backend is "
                        "installed. Component inspection and basic schematic creation "
                        "still work through the repo-owned clean-room parser, but "
                        "symbol-level edits, DLL block authoring, and component "
                        "add/remove/rename operations require an editor backend."
                    )
                ),
            )
        )

    topology_authoring_tools = _supported_tools(available_tools, _TOPOLOGY_AUTHORING_TOOLS)
    if topology_authoring_tools:
        groups.append(
            _group_summary(
                name="topology_authoring",
                title="Topology Authoring",
                state="healthy",
                tools=topology_authoring_tools,
            )
        )

    topology_knowledge_tools = _supported_tools(available_tools, _TOPOLOGY_KNOWLEDGE_TOOLS)
    if topology_knowledge_tools:
        groups.append(
            _group_summary(
                name="topology_knowledge_pack",
                title="Topology Knowledge Pack",
                state="healthy",
                tools=topology_knowledge_tools,
            )
        )

    companion_tools = _supported_tools(available_tools, _COMPANION_EXPORT_TOOLS)
    if companion_tools:
        groups.append(
            _group_summary(
                name="companion_qux_exports",
                title="Companion QUX Exports",
                state="healthy" if qux_available else "degraded",
                tools=companion_tools,
                reason=None if qux_available else qux_reason,
            )
        )

    raw_export_tools = _supported_tools(available_tools, _EXTENDED_RAW_EXPORT_TOOLS)
    if raw_export_tools:
        groups.append(
            _group_summary(
                name="extended_raw_export",
                title="Extended Derived Raw Export",
                state="healthy" if rawwrite_backend is not None else "partial",
                tools=raw_export_tools,
                reason=(
                    None
                    if rawwrite_backend is not None
                    else (
                        "Optional RawWrite is unavailable. Real-valued shared "
                        "time/frequency-axis exports, export_derived_raw stepped "
                        "real time/frequency reconstruction, and complex single-step "
                        "frequency exports stay available through the repo-owned "
                        "clean-room writer, but broader raw dialect "
                        "coverage remains unavailable."
                    )
                ),
            )
        )

    live_gui_tools = _supported_tools(available_tools, _LIVE_GUI_TOOLS)
    if live_gui_tools:
        live_gui_ready = bool(settings.live_gui_bridge_command) and sys.platform == "win32"
        groups.append(
            _group_summary(
                name="live_gui_optional",
                title="Live GUI Optional Layer",
                state="healthy" if live_gui_ready else "partial",
                tools=live_gui_tools,
                reason=(
                    None
                    if live_gui_ready
                    else (
                        "Live GUI manifest scaffolding and runtime session management are "
                        "implemented, "
                        "but launch still depends on a configured external Windows-message bridge "
                        "command and a Windows host."
                    )
                ),
            )
        )

    return tuple(groups)


def _feature_flags(tools: tuple[ToolDefinition, ...]) -> dict[str, object]:
    definition = build_server_definition()
    flags: dict[str, object] = dict(definition.features.model_dump())
    tool_names = _tool_names(tools)
    prepare_monte_carlo = next((tool for tool in tools if tool.name == "prepare_monte_carlo"), None)
    properties = (
        prepare_monte_carlo.input_schema.get("properties", {})
        if prepare_monte_carlo is not None
        else {}
    )
    flags.update(
        {
            "native_mc_staging": isinstance(properties, dict) and "stage_native_mc" in properties,
            "local_remote_sessions": {
                "submit_remote_simulation",
                "poll_remote_run",
                "download_remote_artifacts",
                "close_remote_session",
            }.issubset(tool_names),
            "restart_safe_batch_rehydration": {
                "submit_batch",
                "get_batch_status",
                "collect_batch_results",
            }.issubset(tool_names),
            "live_gui_manifest_scaffolding": {
                "describe_live_gui_support",
                "scaffold_live_gui_session",
            }.issubset(tool_names),
            "live_gui_runtime_management": {
                "launch_live_gui_session",
                "poll_live_gui_session",
                "close_live_gui_session",
            }.issubset(tool_names),
            "live_gui_bidirectional_bridge": {
                "launch_live_gui_session",
                "send_live_gui_session_command",
                "poll_live_gui_session_events",
                "close_live_gui_session",
            }.issubset(tool_names),
            "live_gui_external_bridge_required": True,
            "clean_room_time_raw_export": True,
            "clean_room_frequency_raw_export": True,
            "clean_room_stepped_real_raw_export": True,
            "clean_room_complex_frequency_raw_export": True,
            "published_error_taxonomy": True,
        }
    )
    return flags


def describe_server_capabilities(
    *,
    settings: QSpiceSettings,
    tools: tuple[ToolDefinition, ...],
) -> dict[str, object]:
    """Return a runtime capability snapshot for the current server environment."""

    effective_settings = settings.normalized()
    definition = build_server_definition()
    probe = probe_qspice(effective_settings)
    adapters = tuple(adapter.summary() for adapter in describe_adapters(probe))
    selected_adapter = _selected_adapter_summary(probe)

    _, rawread_backend = _load_rawread_factory()
    _, _, rawwrite_backend = load_rawwrite_api()
    qsch_editor_factory, qsch_editor_backend = load_qsch_editor_factory()
    qux_support = describe_qux_export_support(settings=effective_settings)
    dll_toolchain = describe_dll_build_toolchain(
        qspice_executable=probe.executable,
    )

    tool_groups = _build_tool_groups(
        tools=tools,
        probe=probe,
        selected_adapter=selected_adapter,
        rawread_backend=rawread_backend,
        rawwrite_backend=rawwrite_backend,
        qsch_editor_backend=qsch_editor_backend,
        qux_available=qux_support.available,
        qux_reason=qux_support.notes[0] if qux_support.notes else None,
        settings=effective_settings,
    )

    return {
        "server": {
            "name": definition.name,
            "title": definition.title,
            "transport": effective_settings.transport,
            "workspace_root": str(effective_settings.workspace_root),
            "log_level": effective_settings.log_level,
            "telemetry_enabled": effective_settings.telemetry_enabled,
            "registered_tool_count": len(tools),
            "registered_tools": [tool.name for tool in tools],
        },
        "telemetry": describe_telemetry_state(
            telemetry_enabled=effective_settings.telemetry_enabled
        ),
        "qspice": {
            "configured": probe.configured,
            "available": probe.exists,
            "executable": str(probe.executable) if probe.executable is not None else None,
            "source": probe.source,
            "version": probe.version,
            "version_source": probe.version_source,
            "note": probe.note,
        },
        "selected_adapter": selected_adapter,
        "adapters": list(adapters),
        "optional_backends": {
            "qsch_editor": {
                "available": qsch_editor_backend is not None and qsch_editor_factory is not None,
                "backend": qsch_editor_backend,
                "notes": (
                    [f"Using {qsch_editor_backend}.QschEditor for schematic editing."]
                    if qsch_editor_backend is not None
                    else [
                        "No compatible QschEditor backend is installed. "
                        "Schematic component inspection and basic creation "
                        "still work through the repo-owned clean-room parser, but "
                        "symbol-level and mutation tools require an editor backend. "
                        "Install with: pip install qspice-mcp[backends]"
                    ]
                ),
            },
            "rawread": {
                "available": rawread_backend is not None,
                "backend": rawread_backend,
                "notes": (
                    [f"Using {rawread_backend}.RawRead for waveform access."]
                    if rawread_backend is not None
                    else [
                        "No compatible RawRead backend is installed; common read-only "
                        "waveform analysis still works for the repo-owned clean-room raw "
                        "format plus the supported external compatibility slices, but "
                        "broader `.qraw` dialect coverage is unavailable."
                    ]
                ),
            },
            "rawwrite": {
                "available": rawwrite_backend is not None,
                "backend": rawwrite_backend,
                "notes": (
                    [f"Using {rawwrite_backend}.RawWrite for broad derived raw dialect coverage."]
                    if rawwrite_backend is not None
                    else [
                        "Optional RawWrite is absent; clean-room raw export "
                        "currently covers real-valued shared time/frequency axes "
                        "plus export_derived_raw stepped real time/frequency exports "
                        "and complex single-step frequency traces."
                    ]
                ),
            },
            "qux_companion": {
                "available": qux_support.available,
                "qspice_executable": (
                    str(qux_support.qspice_executable)
                    if qux_support.qspice_executable is not None
                    else None
                ),
                "qux_path": str(qux_support.qux_path) if qux_support.qux_path is not None else None,
                "supported_export_formats": list(qux_support.supported_export_formats),
                "supported_switches": list(qux_support.supported_switches),
                "notes": list(qux_support.notes),
            },
            "dll_build_toolchain": dll_toolchain.as_dict(),
        },
        "error_taxonomy": describe_error_taxonomy(),
        "feature_flags": _feature_flags(tools),
        "guidance": _guidance_summary(),
        "tool_groups": list(tool_groups),
        "degraded_groups": [group for group in tool_groups if group["state"] != "healthy"],
        "workflow_hints": {
            "scratch_buck_authoring": {
                "description": (
                    "Track A: build buck from empty workspace using authoring tools only "
                    "(no materialize_reference_circuit)."
                ),
                "instruction_id": "buck-converter-cpp",
                "list_instructions_tool": "list_workflow_instructions",
                "read_instruction_tool": "read_workflow_instruction",
                "preflight_tool": "describe_topology_authoring_support",
            },
            "reference_recipe_catalog": {
                "description": (
                    "Track B: discover bundled canonical recipes, read catalog instructions, "
                    "and optionally materialize them into the workspace."
                ),
                "instruction_id": "buck-converter-cpp-catalog",
                "list_recipes_tool": "list_reference_circuit_recipes",
                "describe_recipe_tool": "describe_reference_circuit_recipe",
                "list_instructions_tool": "list_workflow_instructions",
                "read_instruction_tool": "read_workflow_instruction",
                "materialize_tool": "materialize_reference_circuit",
            },
        },
    }


__all__ = ["describe_server_capabilities"]
