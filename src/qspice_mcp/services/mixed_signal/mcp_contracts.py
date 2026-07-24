"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "describe_mixed_signal_support": {
        "title": "Describe Mixed-Signal Support",
        "description": "Describe which mixed-signal custom-device scaffold generators (.DLL, Verilog, socket, Python) are available.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "validate_dll_symbol_signature": {
        "title": "Validate DLL Symbol Signature",
        "description": "Cross-check one `.DLL` schematic symbol against a C or C++ source file, including export name, pin count, ordering, and input/output labels.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "source_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "source_path": {"type": "string"},
            },
        },
    },
    "build_dll_device": {
        "title": "Build DLL Device",
        "description": "Compile a workspace C or C++ source file into a `.dll` custom device using QSpice-bundled DMC, MSVC (`cl`), or CMake. `auto` prefers DMC when QSPICE_EXE resolves, then MSVC, then CMake.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_path": {"type": "string"},
                "toolchain": {"type": "string", "enum": ["auto", "dmc", "msvc", "cmake"]},
                "timeout_s": {"type": "number"},
            },
        },
    },
    "scaffold_dll_device": {
        "title": "Scaffold DLL Device",
        "description": "Generate a C++ DLL custom-device project scaffold with the documented QSpice entry points (dll_device_count, dll_device, dll_device_end). When schematic_path is provided, the .cpp and CMakeLists.txt are placed next to the schematic so QSpice's Show Source can find them.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {
                "device_name": {"type": "string"},
                "output_dir": {"type": "string"},
                "schematic_path": {"type": "string"},
            },
        },
    },
    "scaffold_dll_device_from_symbol": {
        "title": "Scaffold DLL Device From Symbol",
        "description": "Generate a C++ DLL custom-device scaffold directly from one existing `.DLL` schematic block so the source stub matches the symbol contract. By default the .cpp and CMakeLists.txt are placed next to the schematic so QSpice's Show Source command can find them automatically.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "output_dir": {"type": "string"},
            },
        },
    },
    "describe_device_spec": {
        "title": "Describe Device Spec",
        "description": "Return the v1 PinDef-style device-spec JSON schema, accepted pin directions, and a bundled example for one-call `.DLL` device creation via create_dll_device_from_spec.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "create_dll_device_from_spec": {
        "title": "Create DLL Device From Spec",
        "description": "Create one `.DLL` custom device from a PinDef-style pin specification in one call: place the block with all pins and (by default) scaffold the matching C++ source. Provide device_name + pins inline, or spec_path pointing to a workspace JSON file ({schema_version: 1, device_name, description?, pins: [{name, direction}]}).",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "device_name": {"type": "string"},
                "pins": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "direction"],
                        "properties": {
                            "name": {"type": "string"},
                            "direction": {"type": "string", "enum": ["input", "output"]},
                        },
                    },
                },
                "spec_path": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "scaffold_source": {"type": "boolean"},
                "output_dir": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "scaffold_verilog_device": {
        "title": "Scaffold Verilog Device",
        "description": "Generate a Verilog module scaffold for use as a QSpice custom device through the documented Verilog device integration path.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {"device_name": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
    "scaffold_socket_device": {
        "title": "Scaffold Socket Device",
        "description": "Generate a Python socket-server scaffold for the documented QSpice socket-based custom-device workflow.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {"device_name": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
    "scaffold_python_device": {
        "title": "Scaffold Python Device",
        "description": "Generate a Python-backed custom-device server scaffold for the documented QSpice Python device integration path.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {"device_name": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
}
