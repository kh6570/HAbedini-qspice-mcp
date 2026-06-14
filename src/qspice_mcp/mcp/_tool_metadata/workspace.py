"""Workspace file tool metadata."""

from __future__ import annotations

from .common import _ann

WORKSPACE_TOOL_METADATA: dict[str, dict[str, object]] = {
    "write_workspace_text_file": {
        "title": "Write Workspace Text File",
        "description": (
            "Write or overwrite one UTF-8 text file inside the workspace root. "
            "For `.c`/`.cpp` C-block sources, compiles the sibling `.dll` automatically "
            "unless build_dll_after_write=false. Pass schematic_path and dll_reference "
            "to validate the DLL symbol against the schematic."
        ),
        "input_schema": {
            "type": "object",
            "required": ["relative_path", "content"],
            "properties": {
                "relative_path": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean"},
                "build_dll_after_write": {
                    "type": "boolean",
                    "description": (
                        "When true (default for .c/.cpp), run build_dll_device after the write."
                    ),
                },
                "schematic_path": {
                    "type": "string",
                    "description": "Optional schematic for validate_dll_symbol_signature.",
                },
                "dll_reference": {
                    "type": "string",
                    "description": "DLL block reference (for example X1) used with schematic_path.",
                },
                "dll_toolchain": {
                    "type": "string",
                    "description": (
                        "Toolchain passed to build_dll_device "
                        "(auto, dmc, msvc, cmake). auto prefers bundled DMC "
                        "when QSPICE_EXE resolves."
                    ),
                },
                "dll_timeout_s": {
                    "type": "number",
                    "description": "Compiler timeout in seconds (default 120).",
                },
            },
        },
        "annotations": _ann(),
    },
    "describe_topology_authoring_support": {
        "title": "Describe Topology Authoring Support",
        "description": (
            "Return a static map of schematic creation capabilities for scratch "
            "topology authoring (Track A), including buck scratch readiness."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "list_workflow_instructions": {
        "title": "List Workflow Instructions",
        "description": (
            "List bundled workflow instructions for scratch circuit authoring "
            "(for example buck-converter-cpp)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_workflow_instruction": {
        "title": "Read Workflow Instruction",
        "description": (
            "Read one bundled workflow instruction document with build steps, "
            "coordinates, and source templates."
        ),
        "input_schema": {
            "type": "object",
            "required": ["instruction_id"],
            "properties": {
                "instruction_id": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
}

__all__ = ["WORKSPACE_TOOL_METADATA"]
