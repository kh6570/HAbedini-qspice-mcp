"""Mixed-signal tool metadata."""

from __future__ import annotations

from .common import _ann

MIXED_SIGNAL_TOOL_METADATA: dict[str, dict[str, object]] = {
    "describe_mixed_signal_support": {
        "title": "Describe Mixed-Signal Support",
        "description": (
            "Describe which mixed-signal custom-device scaffold generators "
            "(.DLL, Verilog, socket, Python) are available."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "validate_dll_symbol_signature": {
        "title": "Validate DLL Symbol Signature",
        "description": (
            "Cross-check one `.DLL` schematic symbol against a C or C++ source file, "
            "including export name, pin count, ordering, and input/output labels."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "source_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "source_path": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "build_dll_device": {
        "title": "Build DLL Device",
        "description": (
            "Compile a workspace C or C++ source file into a `.dll` custom device "
            "using QSpice-bundled DMC, MSVC (`cl`), or CMake. "
            "`auto` prefers DMC when QSPICE_EXE resolves, then MSVC, then CMake."
        ),
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_path": {"type": "string"},
                "toolchain": {
                    "type": "string",
                    "enum": ["auto", "dmc", "msvc", "cmake"],
                },
                "timeout_s": {"type": "number"},
            },
        },
        "annotations": _ann(),
    },
    "scaffold_dll_device": {
        "title": "Scaffold DLL Device",
        "description": (
            "Generate a C++ DLL custom-device project scaffold with the documented "
            "QSpice entry points (dll_device_count, dll_device, dll_device_end). "
            "When schematic_path is provided, the .cpp and CMakeLists.txt are placed "
            "next to the schematic so QSpice's Show Source can find them."
        ),
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {
                "device_name": {"type": "string"},
                "output_dir": {"type": "string"},
                "schematic_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "scaffold_dll_device_from_symbol": {
        "title": "Scaffold DLL Device From Symbol",
        "description": (
            "Generate a C++ DLL custom-device scaffold directly from one existing `.DLL` "
            "schematic block so the source stub matches the symbol contract. "
            "By default the .cpp and CMakeLists.txt are placed next to the schematic "
            "so QSpice's Show Source command can find them automatically."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "output_dir": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "scaffold_verilog_device": {
        "title": "Scaffold Verilog Device",
        "description": (
            "Generate a Verilog module scaffold for use as a QSpice custom device "
            "through the documented Verilog device integration path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {
                "device_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "scaffold_socket_device": {
        "title": "Scaffold Socket Device",
        "description": (
            "Generate a Python socket-server scaffold for the documented QSpice "
            "socket-based custom-device workflow."
        ),
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {
                "device_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "scaffold_python_device": {
        "title": "Scaffold Python Device",
        "description": (
            "Generate a Python-backed custom-device server scaffold for the "
            "documented QSpice Python device integration path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {
                "device_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
}


__all__ = ["MIXED_SIGNAL_TOOL_METADATA"]
