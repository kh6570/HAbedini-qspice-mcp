"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
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
    },
}
