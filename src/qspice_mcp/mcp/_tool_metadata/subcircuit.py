"""Subcircuit tool metadata."""

from __future__ import annotations

from .common import _SCALAR_VALUE, _STEP_FILTER_VALUE, _ann

SUBCIRCUIT_TOOL_METADATA: dict[str, dict[str, object]] = {
    "list_subcircuits": {
        "title": "List Subcircuits",
        "description": "Enumerate subcircuit instances referenced by a schematic.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "instance_path": {"type": "array", "items": {"type": "string"}},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_subcircuit": {
        "title": "Read Subcircuit",
        "description": "Return a resolved view of one subcircuit instance or definition.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "scope": {"type": "string", "enum": ["instance", "definition"]},
                "instance_path": {"type": "array", "items": {"type": "string"}},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "set_subcircuit_component_value": {
        "title": "Set Subcircuit Component Value",
        "description": "Update one component value inside a subcircuit instance or definition.",
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "component_reference", "value"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "component_reference": {"type": "string"},
                "value": _SCALAR_VALUE,
                "scope": {"type": "string", "enum": ["instance", "definition"]},
                "instance_path": {"type": "array", "items": {"type": "string"}},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "set_subcircuit_component_parameters": {
        "title": "Set Subcircuit Component Parameters",
        "description": (
            "Update one component parameter set inside a subcircuit instance or definition."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path", "reference", "component_reference", "parameters"],
            "properties": {
                "schematic_path": {"type": "string"},
                "reference": {"type": "string"},
                "component_reference": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": _STEP_FILTER_VALUE,
                },
                "scope": {"type": "string", "enum": ["instance", "definition"]},
                "instance_path": {"type": "array", "items": {"type": "string"}},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
}


__all__ = ["SUBCIRCUIT_TOOL_METADATA"]
