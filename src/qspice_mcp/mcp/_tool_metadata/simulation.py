"""Simulation tool metadata."""

from __future__ import annotations

from .common import _RETAINED_ARTIFACT_POLICY, _SCALAR_VALUE, _STEP_FILTER_VALUE, _ann

SIMULATION_TOOL_METADATA: dict[str, dict[str, object]] = {
    "generate_netlist": {
        "title": "Generate Netlist",
        "description": "Resolve or stage the derived .net or .cir artifact used for execution.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(idempotent=True),
    },
    "save_netlist_copy": {
        "title": "Save Netlist Copy",
        "description": (
            "Resolve or generate one derived .net or .cir artifact at a requested destination."
        ),
        "input_schema": {
            "type": "object",
            "required": ["source_path", "output_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(idempotent=True),
    },
    "prepare_bode_analysis": {
        "title": "Prepare Bode Analysis",
        "description": (
            "Stage a schematic or netlist with a documented `.bode` directive "
            "for closed-loop SMPS analysis."
        ),
        "input_schema": {
            "type": "object",
            "required": [
                "source_path",
                "perturbation_source",
                "settling_time",
                "start_frequency",
                "stop_frequency",
                "injection_amplitude",
            ],
            "properties": {
                "source_path": {"type": "string"},
                "perturbation_source": {"type": "string"},
                "settling_time": {"type": "string"},
                "start_frequency": {"type": "string"},
                "stop_frequency": {"type": "string"},
                "injection_amplitude": {"type": "string"},
                "square_periods": {"type": "integer", "minimum": 1},
                "debug": {"type": "boolean"},
                "skip_bias_point": {"type": "boolean"},
                "use_initial_conditions": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "prepare_transient": {
        "title": "Prepare Transient Analysis",
        "description": "Stage a schematic or netlist with a documented `.tran` directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "step", "stop"],
            "properties": {
                "source_path": {"type": "string"},
                "step": {"type": "string"},
                "stop": {"type": "string"},
                "start": {"type": "string"},
                "max_step": {"type": "string"},
                "use_initial_conditions": {"type": "boolean"},
                "skip_bias_point": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "prepare_monte_carlo": {
        "title": "Prepare Monte Carlo",
        "description": (
            "Persist explicit Monte Carlo parameter samples for later copy-on-write execution."
        ),
        "input_schema": {
            "type": "object",
            "required": ["source_path", "sample_count"],
            "anyOf": [
                {"required": ["parameters"]},
                {"required": ["component_values"]},
                {"required": ["component_presets"]},
            ],
            "properties": {
                "source_path": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "required": ["nominal"],
                        "properties": {
                            "nominal": {"type": "number"},
                            "tolerance_pct": {"type": "number", "minimum": 0},
                            "minimum": {"type": "number"},
                            "maximum": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                },
                "component_values": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "nominal": {"type": "number"},
                            "tolerance_pct": {"type": "number", "minimum": 0},
                            "minimum": {"type": "number"},
                            "maximum": {"type": "number"},
                        },
                        "anyOf": [
                            {"required": ["nominal"]},
                            {"required": ["tolerance_pct"]},
                            {"required": ["minimum", "maximum"]},
                        ],
                        "additionalProperties": False,
                    },
                },
                "component_presets": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "required": ["tolerance_pct"],
                        "properties": {"tolerance_pct": {"type": "number", "minimum": 0}},
                        "additionalProperties": False,
                    },
                },
                "sample_count": {"type": "integer", "minimum": 1},
                "seed": {"type": "integer"},
                "stage_native_mc": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "prepare_worst_case": {
        "title": "Prepare Worst Case",
        "description": "Persist explicit worst-case corner assignments for later execution.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "anyOf": [
                {"required": ["parameters"]},
                {"required": ["component_values"]},
                {"required": ["component_presets"]},
            ],
            "properties": {
                "source_path": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "required": ["nominal"],
                        "properties": {
                            "nominal": {"type": "number"},
                            "tolerance_pct": {"type": "number", "minimum": 0},
                            "minimum": {"type": "number"},
                            "maximum": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                },
                "component_values": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "nominal": {"type": "number"},
                            "tolerance_pct": {"type": "number", "minimum": 0},
                            "minimum": {"type": "number"},
                            "maximum": {"type": "number"},
                        },
                        "anyOf": [
                            {"required": ["nominal"]},
                            {"required": ["tolerance_pct"]},
                            {"required": ["minimum", "maximum"]},
                        ],
                        "additionalProperties": False,
                    },
                },
                "component_presets": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "object",
                        "required": ["tolerance_pct"],
                        "properties": {"tolerance_pct": {"type": "number", "minimum": 0}},
                        "additionalProperties": False,
                    },
                },
                "mode": {"type": "string", "enum": ["corners", "one_at_a_time"]},
                "include_nominal": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "list_plot_suggestions": {
        "title": "List Plot Suggestions",
        "description": (
            "Inspect a schematic or netlist and surface `.plot`, `.print`, "
            "`.probe`, and `.abscissa` hints."
        ),
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "netlist_output_path": {"type": "string"},
            },
        },
        "annotations": _ann(),
    },
    "summarize_tolerance_analysis": {
        "title": "Summarize Tolerance Analysis",
        "description": (
            "Summarize Monte Carlo or worst-case target coverage and numeric `.meas` results from "
            "a persisted batch; measure refresh requires sibling run netlists and QPOST, or pass "
            "`refresh_measures=false` to use recorded `.meas` artifacts."
        ),
        "input_schema": {
            "type": "object",
            "required": ["batch_path"],
            "properties": {
                "batch_path": {"type": "string"},
                "measures": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "refresh_measures": {"type": "boolean"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "run_simulation": {
        "title": "Run Simulation",
        "description": "Plan or run QSpice for a .qsch, .cir, or .net source path.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "log_path": {"type": "string"},
                "raw_output_path": {"type": "string"},
                "netlist_output_path": {"type": "string"},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
            },
        },
        "annotations": _ann(),
    },
    "run_value_sweep": {
        "title": "Run Value Sweep",
        "description": "Run one schematic across multiple component values.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "reference", "values"],
            "properties": {
                "source_path": {"type": "string"},
                "reference": {"type": "string"},
                "values": {
                    "type": "array",
                    "minItems": 1,
                    "items": _SCALAR_VALUE,
                },
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
        "annotations": _ann(),
    },
    "run_param_sweep": {
        "title": "Run Parameter Sweep",
        "description": "Run one schematic across the Cartesian product of parameter values.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "parameters"],
            "properties": {
                "source_path": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "propertyNames": {"type": "string"},
                    "additionalProperties": {
                        "type": "array",
                        "minItems": 1,
                        "items": _STEP_FILTER_VALUE,
                    },
                },
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
        "annotations": _ann(),
    },
    "run_monte_carlo": {
        "title": "Run Monte Carlo",
        "description": "Run one prepared Monte Carlo plan as a copy-on-write batch.",
        "input_schema": {
            "type": "object",
            "required": ["prepared_path"],
            "properties": {
                "prepared_path": {"type": "string"},
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
        "annotations": _ann(),
    },
    "run_worst_case": {
        "title": "Run Worst Case",
        "description": "Run one prepared worst-case plan as a copy-on-write batch.",
        "input_schema": {
            "type": "object",
            "required": ["prepared_path"],
            "properties": {
                "prepared_path": {"type": "string"},
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
        "annotations": _ann(),
    },
    "run_model_sweep": {
        "title": "Run Model Sweep",
        "description": "Run one schematic across multiple element models.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "reference", "models"],
            "properties": {
                "source_path": {"type": "string"},
                "reference": {"type": "string"},
                "models": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "output_dir": {"type": "string"},
                "parallelism": {"type": "integer", "minimum": 1},
                "dry_run": {"type": "boolean"},
                "timeout_s": {"type": "number", "minimum": 0},
                "ascii_raw": {"type": "boolean"},
                "extra_switches": {"type": "array", "items": {"type": "string"}},
                "resume": {"type": "boolean"},
                "retained_artifact_policy": _RETAINED_ARTIFACT_POLICY,
            },
        },
        "annotations": _ann(),
    },
}


__all__ = ["SIMULATION_TOOL_METADATA"]
