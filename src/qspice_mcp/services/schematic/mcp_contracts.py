"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

from qspice_mcp.services._internals.mcp_schema_common import (
    _SCALAR_VALUE,
    _STEP_FILTER_VALUE,
)

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "read_net_connectivity": {
        "title": "Read Net Connectivity",
        "description": "Report electrical nets and the component pins attached to each for a supported clean-room `.qsch` schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {"schematic_path": {"type": "string"}},
        },
    },
    "check_schematic": {
        "title": "Check Schematic",
        "description": "Run read-only ERC-style checks on a supported `.qsch` schematic: missing ground reference, floating pins, duplicate reference designators, missing component value or model, and conflicting net labels.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {"schematic_path": {"type": "string"}},
        },
    },
    "check_netlist": {
        "title": "Check Netlist",
        "description": "Run read-only ERC-style checks on a `.net` or `.cir` netlist: missing ground node 0, duplicate reference designators, and single-connection nodes.",
        "input_schema": {
            "type": "object",
            "required": ["netlist_path"],
            "properties": {"netlist_path": {"type": "string"}},
        },
    },
    "compare_schematics": {
        "title": "Compare Schematics",
        "description": "Diff two supported `.qsch` schematics, reporting added, removed, and changed components (value, model, position) plus net-count differences.",
        "input_schema": {
            "type": "object",
            "required": ["base_path", "revised_path"],
            "properties": {
                "base_path": {"type": "string"},
                "revised_path": {"type": "string"},
            },
        },
    },
    "move_component_preserving_connections": {
        "title": "Move Component Preserving Connections",
        "description": "Deprecated alias: prefer set_component_position, which now preserves connections by default. Move and/or rotate one placed component and follow attached wire endpoints, junctions, and net labels so existing connections stay intact. Provide at least one of position_x, position_y, or rotation_degrees.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_library_component": {
        "title": "Add Library Component",
        "description": "Clone one component symbol (symbol name, library file, drawing primitives, and pins) from a reference template `.qsch` into a target schematic at a position, assigning a new reference designator.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "template_path", "template_reference", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "template_path": {"type": "string"},
                "template_reference": {"type": "string"},
                "reference": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "value": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "export_symbol_to_qsym": {
        "title": "Export Symbol To Qsym",
        "description": "Export one embedded component symbol from a schematic to a standalone `.qsym` symbol file (same guillemet wire format as `.qsch`) for reuse across schematics and external symbol libraries.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "output_path": {"type": "string"},
                "symbol_name": {"type": "string"},
            },
        },
    },
    "add_component_from_qsym": {
        "title": "Add Component From Qsym",
        "description": "Place one component into a schematic from a standalone `.qsym` symbol file, embedding the full symbol (drawing, pins, type, library file) and assigning a new reference designator.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "qsym_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "qsym_path": {"type": "string"},
                "reference": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "value": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "render_schematic_image": {
        "title": "Render Schematic Image",
        "description": "Render a supported `.qsch` schematic (wires, junctions, component anchors with refdes/value, and net labels) to a PNG image inside the workspace.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "output_path": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
        },
    },
    "materialize_reference_circuit": {
        "title": "Materialize Reference Circuit",
        "description": "Write server-bundled reference circuit files into the workspace so an empty folder can reproduce a canonical example (for example buck_converter_cpp) from bundled package data recipes.",
        "input_schema": {
            "type": "object",
            "required": ["recipe_id"],
            "properties": {
                "recipe_id": {"type": "string"},
                "output_dir": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
        },
    },
    "import_circuit_bundle": {
        "title": "Import Circuit Bundle",
        "description": "Copy one workspace-local `.qsch` schematic and sibling sidecar files into a destination folder.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "output_dir": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
        },
    },
    "create_schematic": {
        "title": "Create Schematic",
        "description": "Create a blank `.qsch` file so later schematic tools can build from scratch.",
        "input_schema": {
            "type": "object",
            "required": ["output_path"],
            "properties": {"output_path": {"type": "string"}, "overwrite": {"type": "boolean"}},
        },
    },
    "create_starter_schematic": {
        "title": "Create Starter Schematic",
        "description": "Create a runnable source-load starter schematic in one call.",
        "input_schema": {
            "type": "object",
            "required": ["output_path"],
            "properties": {
                "output_path": {"type": "string"},
                "overwrite": {"type": "boolean"},
                "source_reference": {"type": "string"},
                "source_value": _SCALAR_VALUE,
                "load_reference": {"type": "string"},
                "load_value": _SCALAR_VALUE,
                "input_net_name": {"type": "string"},
                "analysis_instruction": {"type": "string"},
            },
        },
    },
    "add_component": {
        "title": "Add Component",
        "description": "Insert one simple part or ground label into a schematic. Supported component_kind values: resistor, capacitor, diode, voltage_source, inductor, behavioral, nmos, pmos, ground (aliases such as l, mn, b also work).",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "component_kind"],
            "properties": {
                "schematic_path": {"type": "string"},
                "component_kind": {
                    "type": "string",
                    "enum": [
                        "resistor",
                        "capacitor",
                        "diode",
                        "voltage_source",
                        "inductor",
                        "behavioral",
                        "nmos",
                        "pmos",
                        "ground",
                    ],
                },
                "reference": {"type": "string"},
                "value": _SCALAR_VALUE,
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "auto_place": {
                    "type": "boolean",
                    "description": (
                        "When true, ignore explicit coordinates and place the part on the "
                        "next collision-free grid slot (left-to-right, 0° rotation)."
                    ),
                },
                "net_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [
                {
                    "if": {
                        "properties": {
                            "component_kind": {
                                "enum": [
                                    "resistor",
                                    "capacitor",
                                    "diode",
                                    "voltage_source",
                                    "inductor",
                                    "behavioral",
                                    "nmos",
                                    "pmos",
                                ]
                            }
                        }
                    },
                    "then": {"required": ["reference", "value"]},
                }
            ],
        },
    },
    "add_dll_block": {
        "title": "Add DLL Block",
        "description": "Insert one `.DLL` custom-device block into a schematic with starter input and output pins.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "device_name"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "device_name": {"type": "string"},
                "input_pin_names": {"type": "array", "items": {"type": "string"}},
                "output_pin_names": {"type": "array", "items": {"type": "string"}},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_dll_block_pin": {
        "title": "Add DLL Block Pin",
        "description": "Insert one input or output pin into an existing `.DLL` block symbol.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "pin_name", "direction"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "pin_name": {"type": "string"},
                "direction": {"type": "string", "enum": ["input", "output"]},
                "insert_index": {"type": "integer", "minimum": 0},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_wire": {
        "title": "Add Wire",
        "description": "Insert one wire segment using raw coordinates or component pin selectors.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "net_name"],
            "properties": {
                "schematic_path": {"type": "string"},
                "start_x": {"type": "integer"},
                "start_y": {"type": "integer"},
                "end_x": {"type": "integer"},
                "end_y": {"type": "integer"},
                "start_reference": {"type": "string"},
                "start_pin": {"type": "string"},
                "end_reference": {"type": "string"},
                "end_pin": {"type": "string"},
                "net_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [
                {
                    "oneOf": [
                        {"required": ["start_x", "start_y"]},
                        {"required": ["start_reference", "start_pin"]},
                    ]
                },
                {
                    "oneOf": [
                        {"required": ["end_x", "end_y"]},
                        {"required": ["end_reference", "end_pin"]},
                    ]
                },
            ],
        },
    },
    "remove_wire": {
        "title": "Remove Wire",
        "description": "Remove one wire segment using raw coordinates or component pin selectors.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "start_x": {"type": "integer"},
                "start_y": {"type": "integer"},
                "end_x": {"type": "integer"},
                "end_y": {"type": "integer"},
                "start_reference": {"type": "string"},
                "start_pin": {"type": "string"},
                "end_reference": {"type": "string"},
                "end_pin": {"type": "string"},
                "net_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [
                {
                    "oneOf": [
                        {"required": ["start_x", "start_y"]},
                        {"required": ["start_reference", "start_pin"]},
                    ]
                },
                {
                    "oneOf": [
                        {"required": ["end_x", "end_y"]},
                        {"required": ["end_reference", "end_pin"]},
                    ]
                },
            ],
        },
    },
    "remove_net_label": {
        "title": "Remove Net Label",
        "description": "Remove one net label from a schematic by position and optional net name.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "position_x", "position_y"],
            "properties": {
                "schematic_path": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "net_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "remove_junction": {
        "title": "Remove Junction",
        "description": "Remove one junction node from a schematic by position.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "position_x", "position_y"],
            "properties": {
                "schematic_path": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_junction": {
        "title": "Add Junction",
        "description": "Insert one junction node into a schematic wire graph.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "position_x", "position_y"],
            "properties": {
                "schematic_path": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_net_label": {
        "title": "Add Net Label",
        "description": "Insert one net label into a schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "position_x", "position_y", "net_name"],
            "properties": {
                "schematic_path": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "net_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "add_instruction": {
        "title": "Add Instruction",
        "description": "Append one analysis instruction line to a schematic using `instruction=`.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "instruction"],
            "properties": {
                "schematic_path": {"type": "string"},
                "instruction": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "inspect_schematic": {
        "title": "Inspect Schematic",
        "description": "Summarize a QSpice schematic before simulation. Set include_parameters=true to also return schematic-level `.param` directives, and include_connectivity=true to attach the net-to-pin connectivity report in the same call.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "include_parameters": {"type": "boolean"},
                "include_connectivity": {"type": "boolean"},
            },
        },
    },
    "list_components": {
        "title": "List Components",
        "description": "Enumerate components from a schematic through an installed editor backend.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {"schematic_path": {"type": "string"}, "prefixes": {"type": "string"}},
        },
    },
    "read_component": {
        "title": "Read Component",
        "description": "Return a normalized view of one component from a schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {"schematic_path": {"type": "string"}, "reference": {"type": "string"}},
        },
    },
    "read_component_symbol": {
        "title": "Read Component Symbol",
        "description": "Return embedded symbol text, pin, drawing-item, and drawing-tag metadata for one component.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {"schematic_path": {"type": "string"}, "reference": {"type": "string"}},
        },
    },
    "add_component_symbol_drawing": {
        "title": "Add Component Symbol Drawing",
        "description": "Insert one embedded symbol drawing item from a raw tag name and argument list.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "tag_name", "arguments"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "tag_name": {"type": "string"},
                "arguments": {"type": "array", "items": {"type": "string"}},
                "insert_index": {"type": "integer", "minimum": 0},
                "output_path": {"type": "string"},
            },
        },
    },
    "save_schematic_as": {
        "title": "Save Schematic As",
        "description": "Write a schematic to a requested `.qsch` path.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "output_path"],
            "properties": {"schematic_path": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
    "set_component_symbol_text": {
        "title": "Set Component Symbol Text",
        "description": "Update one embedded symbol text item, including layout and style attributes.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "text_index": {"type": "integer", "minimum": 0},
                "text_role": {"type": "string", "enum": ["reference", "value"]},
                "text": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "size": {"type": "integer"},
                "rotation_code": {"type": "integer"},
                "is_comment": {"type": "boolean"},
                "color_code": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [
                {"oneOf": [{"required": ["text_index"]}, {"required": ["text_role"]}]},
                {
                    "anyOf": [
                        {"required": ["text"]},
                        {"required": ["position_x", "position_y"]},
                        {"required": ["size"]},
                        {"required": ["rotation_code"]},
                        {"required": ["is_comment"]},
                        {"required": ["color_code"]},
                    ]
                },
            ],
        },
    },
    "normalize_component_text_rotation": {
        "title": "Normalize Component Text Rotation",
        "description": (
            "Reset refdes/value symbol text to left-to-right readable orientation, "
            "optionally compensating for the component body rotation."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "text_roles": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["reference", "refdes", "value"]},
                },
                "compensate_component_rotation": {"type": "boolean"},
                "upright_rotation_code": {"type": "integer"},
                "output_path": {"type": "string"},
            },
        },
    },
    "set_component_symbol_drawing": {
        "title": "Set Component Symbol Drawing",
        "description": "Update one embedded symbol drawing item by replacing its tag name or raw arguments.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "drawing_index"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "drawing_index": {"type": "integer", "minimum": 0},
                "tag_name": {"type": "string"},
                "arguments": {"type": "array", "items": {"type": "string"}},
                "output_path": {"type": "string"},
            },
            "allOf": [{"anyOf": [{"required": ["tag_name"]}, {"required": ["arguments"]}]}],
        },
    },
    "set_component_symbol_pin": {
        "title": "Set Component Symbol Pin",
        "description": "Update one embedded symbol pin name, label geometry, or pin-kind metadata.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "pin_index": {"type": "integer", "minimum": 0},
                "pin_name": {"type": "string"},
                "new_pin_name": {"type": "string"},
                "label_position_x": {"type": "integer"},
                "label_position_y": {"type": "integer"},
                "text_size": {"type": "integer"},
                "label_anchor_code": {"type": "integer"},
                "pin_kind_code": {"type": "integer"},
                "color_code": {"type": "string"},
                "aux_code": {"type": "integer"},
                "behavioral_net_override": {"type": "string"},
                "clear_behavioral_net_override": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
            "allOf": [
                {"oneOf": [{"required": ["pin_index"]}, {"required": ["pin_name"]}]},
                {
                    "anyOf": [
                        {"required": ["new_pin_name"]},
                        {"required": ["label_position_x", "label_position_y"]},
                        {"required": ["text_size"]},
                        {"required": ["label_anchor_code"]},
                        {"required": ["pin_kind_code"]},
                        {"required": ["color_code"]},
                        {"required": ["aux_code"]},
                        {"required": ["behavioral_net_override"]},
                        {"required": ["clear_behavioral_net_override"]},
                    ]
                },
            ],
        },
    },
    "set_dll_block_pin_role": {
        "title": "Set DLL Block Pin Role",
        "description": "Move one `.DLL` block pin into the input or output role preset.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "pin_role"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "pin_role": {"type": "string", "enum": ["input", "output"]},
                "pin_index": {"type": "integer", "minimum": 0},
                "pin_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [{"oneOf": [{"required": ["pin_index"]}, {"required": ["pin_name"]}]}],
        },
    },
    "remove_component": {
        "title": "Remove Component",
        "description": "Remove one schematic component by reference and persist the edited schematic. Set remove_orphan_wires=true to also prune wires, junctions, and net labels left dangling by the deletion (off by default).",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "remove_orphan_wires": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
    },
    "remove_component_symbol_drawing": {
        "title": "Remove Component Symbol Drawing",
        "description": "Remove one embedded symbol drawing item by index.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "drawing_index"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "drawing_index": {"type": "integer", "minimum": 0},
                "output_path": {"type": "string"},
            },
        },
    },
    "remove_dll_block_pin": {
        "title": "Remove DLL Block Pin",
        "description": "Remove one pin from an existing `.DLL` block symbol.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "pin_index": {"type": "integer", "minimum": 0},
                "pin_name": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "allOf": [{"oneOf": [{"required": ["pin_index"]}, {"required": ["pin_name"]}]}],
        },
    },
    "set_component_value": {
        "title": "Set Component Value",
        "description": "Update the value field of one schematic component.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "value"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "value": _SCALAR_VALUE,
                "output_path": {"type": "string"},
            },
        },
    },
    "set_component_rotation": {
        "title": "Set Component Rotation",
        "description": "Deprecated alias for set_component_position (rotation only). Rotate one placed component in 45-degree steps; attached wires/junctions/net labels follow the pins and refdes/value text is reset upright by default. Set preserve_connections=false or normalize_text=false to opt out.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "rotation_degrees"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "rotation_degrees": {"type": "integer"},
                "preserve_connections": {"type": "boolean"},
                "normalize_text": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
    },
    "set_component_position": {
        "title": "Set Component Position",
        "description": "Unified placement tool: move and/or rotate one placed component. Attached wires, junctions, and net labels follow the pins by default (preserve_connections) and refdes/value text is reset to upright readability by default (normalize_text). Provide at least one of position_x, position_y, or rotation_degrees. Set preserve_connections=false or normalize_text=false to opt out.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "position_x": {"type": "integer"},
                "position_y": {"type": "integer"},
                "rotation_degrees": {"type": "integer"},
                "preserve_connections": {"type": "boolean"},
                "normalize_text": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
            "anyOf": [
                {"required": ["position_x", "position_y"]},
                {"required": ["rotation_degrees"]},
            ],
        },
    },
    "set_component_parameters": {
        "title": "Set Component Parameters",
        "description": "Update one or more component-local parameters in a schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "parameters"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": _STEP_FILTER_VALUE,
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "set_element_model": {
        "title": "Set Element Model",
        "description": "Update the model text of one schematic component.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "model"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "model": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "set_parameter": {
        "title": "Set Parameter",
        "description": "Update one schematic-level `.param` directive.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "name", "value"],
            "properties": {
                "schematic_path": {"type": "string"},
                "name": {"type": "string"},
                "value": _SCALAR_VALUE,
                "output_path": {"type": "string"},
            },
        },
    },
    "remove_instruction": {
        "title": "Remove Instruction",
        "description": "Remove one exact or regex-matched directive from a schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "instruction"],
            "properties": {
                "schematic_path": {"type": "string"},
                "instruction": {"type": "string"},
                "output_path": {"type": "string"},
                "regex": {"type": "boolean"},
            },
        },
    },
    "rename_component_reference": {
        "title": "Rename Component Reference",
        "description": "Rename one schematic component reference, updating both the component and its embedded symbol text.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "new_reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "new_reference": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "describe_schematic_edit_support": {
        "title": "Describe Schematic Edit Support",
        "description": "Return a static machine-readable capability map for every known schematic edit intent so AI clients can make deterministic go/no-go decisions before attempting writes.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "describe_edit_capability": {
        "title": "Describe Edit Capability",
        "description": "Perform a preflight check for one edit intent on a component: read its current state, map the intent to the correct tool, and return either a ready-to-execute suggestion or a clear explanation plus nearest valid alternatives.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "intent"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "intent": {
                    "type": "string",
                    "enum": [
                        "rename_reference",
                        "change_value",
                        "change_model",
                        "edit_parameters",
                        "move_component",
                        "rotate_component",
                        "edit_symbol_text",
                        "edit_symbol_pin",
                        "edit_symbol_drawing",
                        "delete_component",
                    ],
                },
            },
        },
    },
    "describe_topology_authoring_support": {
        "title": "Describe Topology Authoring Support",
        "description": "Return a static map of schematic creation capabilities for scratch topology authoring (Track A), including buck scratch readiness.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "suggest_component_placement": {
        "title": "Suggest Component Placement",
        "description": (
            "Suggest collision-free schematic coordinates for the next component using "
            "a readable left-to-right grid with upright (0°) rotation."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "component_kind"],
            "properties": {
                "schematic_path": {"type": "string"},
                "component_kind": {
                    "type": "string",
                    "enum": [
                        "resistor",
                        "capacitor",
                        "diode",
                        "voltage_source",
                        "inductor",
                        "behavioral",
                        "nmos",
                        "pmos",
                        "ground",
                        "dll_block",
                    ],
                },
                "origin_x": {"type": "integer"},
                "origin_y": {"type": "integer"},
                "grid_step_x": {"type": "integer"},
                "grid_step_y": {"type": "integer"},
                "clearance_units": {"type": "integer"},
                "max_columns": {"type": "integer"},
                "max_rows": {"type": "integer"},
            },
        },
    },
    "describe_schematic_layout_spec": {
        "title": "Describe Schematic Layout Spec",
        "description": (
            "Return the v1 JSON layout-spec schema, placement modes, and bundled example "
            "for batch component placement without large coordinate tables."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    "apply_schematic_layout_spec": {
        "title": "Apply Schematic Layout Spec",
        "description": (
            "Place schematic components in batch from a workspace JSON layout specification "
            "using auto, grid, or absolute placement modes."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "spec_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "spec_path": {"type": "string"},
                "skip_existing": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
    },
}
