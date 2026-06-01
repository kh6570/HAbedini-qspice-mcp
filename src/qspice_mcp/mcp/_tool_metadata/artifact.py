"""Artifact tool metadata."""

from __future__ import annotations

from .common import _COMPONENT, _STEP_FILTERS, _ann

ARTIFACT_TOOL_METADATA: dict[str, dict[str, object]] = {
    "describe_qux_export_support": {
        "title": "Describe QUX Export Support",
        "description": (
            "Describe whether the companion QUX executable is available and "
            "which documented export switches it supports."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "export_derived_raw": {
        "title": "Export Derived Raw",
        "description": (
            "Write one filtered waveform selection to a derived binary raw artifact, "
            "with optional stepped reconstruction."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signals"],
            "properties": {
                "raw_path": {"type": "string"},
                "signals": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "output_path": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "all_steps": {"type": "boolean"},
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
        },
        "annotations": _ann(),
    },
    "merge_waveforms": {
        "title": "Merge Waveforms",
        "description": (
            "Merge multiple filtered waveform selections into one derived raw artifact, "
            "with optional stepped reconstruction."
        ),
        "input_schema": {
            "type": "object",
            "required": ["inputs"],
            "properties": {
                "inputs": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["raw_path", "signal"],
                        "properties": {
                            "raw_path": {"type": "string"},
                            "signal": {"type": "string"},
                            "label": {"type": "string"},
                            "step": {"type": "integer", "minimum": 0},
                            "step_filters": _STEP_FILTERS,
                            "component": _COMPONENT,
                            "t_start": {"type": "number"},
                            "t_end": {"type": "number"},
                        },
                    },
                },
                "output_path": {"type": "string"},
                "all_steps": {"type": "boolean"},
            },
        },
        "annotations": _ann(),
    },
    "export_waveform_ascii": {
        "title": "Export Waveform ASCII",
        "description": (
            "Export one or more waveform expressions through the documented QUX ASCII export path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "expressions"],
            "properties": {
                "raw_path": {"type": "string"},
                "expressions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "point_count": {"type": "integer", "minimum": 2},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "export_waveform_csv": {
        "title": "Export Waveform CSV",
        "description": (
            "Export one or more waveform expressions through the documented QUX CSV export path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "expressions"],
            "properties": {
                "raw_path": {"type": "string"},
                "expressions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "point_count": {"type": "integer", "minimum": 2},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "export_waveform_spice": {
        "title": "Export Waveform SPICE",
        "description": (
            "Export one or more waveform expressions through the documented QUX SPICE export path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "expressions"],
            "properties": {
                "raw_path": {"type": "string"},
                "expressions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "point_count": {"type": "integer", "minimum": 2},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "export_touchstone_s2p": {
        "title": "Export Touchstone S2P",
        "description": (
            "Export one or more waveform expressions through the documented "
            "QUX Touchstone S2P path."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "expressions"],
            "properties": {
                "raw_path": {"type": "string"},
                "expressions": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "point_count": {"type": "integer", "minimum": 2},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "generate_dll_variables": {
        "title": "Generate DLL Variables",
        "description": (
            "Generate `.DLL` variable declarations through the documented QUX companion command."
        ),
        "input_schema": {
            "type": "object",
            "required": ["schematic_path"],
            "properties": {
                "schematic_path": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "summarize_batch": {
        "title": "Summarize Batch",
        "description": "Summarize a persisted batch manifest and its derived artifacts.",
        "input_schema": {
            "type": "object",
            "required": ["batch_path"],
            "properties": {"batch_path": {"type": "string"}},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "export_measures_csv": {
        "title": "Export Measures CSV",
        "description": "Export measurement rows from a persisted batch manifest to CSV.",
        "input_schema": {
            "type": "object",
            "required": ["batch_path"],
            "properties": {
                "batch_path": {"type": "string"},
                "output_path": {"type": "string"},
                "measures": {"type": "array", "items": {"type": "string"}},
                "refresh_measures": {"type": "boolean"},
            },
        },
        "annotations": _ann(),
    },
    "compare_waveforms": {
        "title": "Compare Waveforms",
        "description": "Compare one scalar waveform measurement across runs in a persisted batch.",
        "input_schema": {
            "type": "object",
            "required": ["batch_path", "signal", "operation"],
            "properties": {
                "batch_path": {"type": "string"},
                "signal": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": [
                        "min",
                        "max",
                        "mean",
                        "rms",
                        "peak_to_peak",
                        "abs_max",
                        "start",
                        "end",
                        "integral",
                    ],
                },
                "baseline_run_index": {"type": "integer", "minimum": 0},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
}


__all__ = ["ARTIFACT_TOOL_METADATA"]
