"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

from qspice_mcp.services._internals.mcp_schema_common import (
    _RETAINED_ARTIFACT_POLICY,
    _SCALAR_VALUE,
    _STEP_FILTER_VALUE,
)

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "generate_netlist": {
        "title": "Generate Netlist",
        "description": "Resolve or stage the derived .net or .cir artifact used for execution.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch`, `.cir`, or `.net` source file.",
                },
                "output_path": {
                    "type": "string",
                    "description": "Optional destination; defaults to the sibling `.net` path.",
                },
            },
        },
    },
    "save_netlist_copy": {
        "title": "Save Netlist Copy",
        "description": "Resolve or generate one derived .net or .cir artifact at a requested destination.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "output_path"],
            "properties": {"source_path": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
    "prepare_bode_analysis": {
        "title": "Prepare Bode Analysis",
        "description": "Stage a schematic or netlist with a documented `.bode` directive for closed-loop SMPS analysis.",
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
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch` or netlist to stage.",
                },
                "perturbation_source": {
                    "type": "string",
                    "description": "Reference of the injection source in the feedback path (e.g. V3).",
                },
                "settling_time": {
                    "type": "string",
                    "description": "Time to reach steady state before injection (e.g. '2m').",
                },
                "start_frequency": {
                    "type": "string",
                    "description": "Sweep start frequency (e.g. '100').",
                },
                "stop_frequency": {
                    "type": "string",
                    "description": "Sweep stop frequency (e.g. '100k').",
                },
                "injection_amplitude": {
                    "type": "string",
                    "description": "Perturbation amplitude; keep small vs. the operating point (e.g. '10m').",
                },
                "square_periods": {"type": "integer", "minimum": 1},
                "debug": {"type": "boolean"},
                "skip_bias_point": {"type": "boolean"},
                "use_initial_conditions": {"type": "boolean"},
                "reference_node": {"type": "string"},
                "bode_amplitude_frequency": {"type": "string"},
                "bode_low_power": {"type": "string"},
                "bode_high_power": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_ac": {
        "title": "Prepare AC Analysis",
        "description": "Stage a schematic or netlist with a documented `.ac` directive (dec/oct/lin sweeps or an explicit frequency list).",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "sweep_type"],
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch` or netlist to stage.",
                },
                "sweep_type": {
                    "type": "string",
                    "enum": ["dec", "oct", "lin", "list"],
                    "description": "Sweep spacing; 'list' uses explicit `frequencies`.",
                },
                "points": {
                    "type": "string",
                    "description": "Points per decade/octave, or total points for 'lin'.",
                },
                "start": {
                    "type": "string",
                    "description": "Start frequency (e.g. '10').",
                },
                "stop": {
                    "type": "string",
                    "description": "Stop frequency (e.g. '1Meg').",
                },
                "frequencies": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                    "description": "Explicit frequency list when sweep_type='list'.",
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_dc_sweep": {
        "title": "Prepare DC Sweep",
        "description": "Stage a schematic or netlist with a documented `.dc` directive (lin/oct/dec/list sweeps, optional second sweep dimension).",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "source"],
            "properties": {
                "source_path": {"type": "string"},
                "source": {"type": "string"},
                "start": {"type": "string"},
                "stop": {"type": "string"},
                "step": {"type": "string"},
                "sweep_mode": {"type": "string", "enum": ["lin", "oct", "dec", "list"]},
                "list_values": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "second_source": {"type": "string"},
                "second_start": {"type": "string"},
                "second_stop": {"type": "string"},
                "second_step": {"type": "string"},
                "second_sweep_mode": {
                    "type": "string",
                    "enum": ["lin", "oct", "dec", "list"],
                },
                "second_list_values": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_loop_gain_analysis": {
        "title": "Prepare Loop Gain Analysis",
        "description": "Stage a schematic or netlist with a documented `.ac` directive and Tian or Middlebrook loop-gain guidance.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "method", "sweep_type", "points", "start", "stop"],
            "properties": {
                "source_path": {"type": "string"},
                "method": {"type": "string", "enum": ["tian", "middlebrook"]},
                "sweep_type": {"type": "string", "enum": ["dec", "oct", "lin"]},
                "points": {"type": "string"},
                "start": {"type": "string"},
                "stop": {"type": "string"},
                "expected_loop_gain_signal": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_noise": {
        "title": "Prepare Noise Analysis",
        "description": "Stage a schematic or netlist with a documented `.noise` directive (dec/oct/lin sweeps or an explicit frequency list).",
        "input_schema": {
            "type": "object",
            "required": [
                "source_path",
                "output_node",
                "input_source",
                "sweep_type",
            ],
            "properties": {
                "source_path": {"type": "string"},
                "output_node": {"type": "string"},
                "input_source": {"type": "string"},
                "sweep_type": {"type": "string", "enum": ["dec", "oct", "lin", "list"]},
                "points": {"type": "string"},
                "start": {"type": "string"},
                "stop": {"type": "string"},
                "frequencies": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_transfer_function": {
        "title": "Prepare Transfer Function Analysis",
        "description": "Stage a schematic or netlist with a documented `.tf` directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "output_node", "input_source"],
            "properties": {
                "source_path": {"type": "string"},
                "output_node": {"type": "string"},
                "input_source": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_sensitivity": {
        "title": "Prepare Sensitivity Analysis",
        "description": "Stage a schematic or netlist with a documented `.sens` directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "analysis_type", "output_node"],
            "properties": {
                "source_path": {"type": "string"},
                "analysis_type": {"type": "string", "enum": ["dc", "ac"]},
                "output_node": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_temperature_sweep": {
        "title": "Prepare Temperature Sweep",
        "description": "Stage a schematic or netlist with a documented `.step temp` directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "start", "stop", "step"],
            "properties": {
                "source_path": {"type": "string"},
                "start": {"type": "string"},
                "stop": {"type": "string"},
                "step": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_transient": {
        "title": "Prepare Transient Analysis",
        "description": "Stage a schematic or netlist with a documented `.tran` directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "step", "stop"],
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch` or netlist to stage.",
                },
                "step": {
                    "type": "string",
                    "description": "Suggested output timestep (e.g. '1u').",
                },
                "stop": {
                    "type": "string",
                    "description": "Simulation end time (e.g. '5m').",
                },
                "start": {
                    "type": "string",
                    "description": "Optional time at which waveform recording starts.",
                },
                "max_step": {
                    "type": "string",
                    "description": "Optional cap on the internal integration timestep.",
                },
                "use_initial_conditions": {
                    "type": "boolean",
                    "description": "Append `uic` to honor `.ic` values instead of solving the bias point.",
                },
                "skip_bias_point": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_op": {
        "title": "Prepare Operating Point Analysis",
        "description": "Stage a schematic or netlist with a documented `.op` bias-point directive.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_save": {
        "title": "Prepare Save Directive",
        "description": "Stage a schematic or netlist with a documented `.save` directive limiting stored waveform traces (wildcards `*` and `?` supported).",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "patterns"],
            "properties": {
                "source_path": {"type": "string"},
                "patterns": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_options": {
        "title": "Prepare Simulator Options",
        "description": "Stage a schematic or netlist with a documented `.options` directive covering convergence (cshunt, gmin, method, ...), Bode/FRA (boderef, bodeampfreq, ...), and output bookkeeping (savepowers, keepopinfo) options.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "cshunt": {"type": "string"},
                "gshunt": {"type": "string"},
                "gmin": {"type": "string"},
                "gminsteps": {"type": "string"},
                "srcsteps": {"type": "string"},
                "noopiter": {"type": "boolean"},
                "feather": {"type": "string"},
                "reltol": {"type": "string"},
                "abstol": {"type": "string"},
                "vntol": {"type": "string"},
                "method": {"type": "string", "enum": ["trap", "gear"]},
                "itl1": {"type": "string"},
                "itl4": {"type": "string"},
                "maxstep": {"type": "string"},
                "max1ststep": {"type": "string"},
                "ric": {"type": "string"},
                "boderef": {"type": "string"},
                "bodeampfreq": {"type": "string"},
                "bodelopow": {"type": "string"},
                "bodehipow": {"type": "string"},
                "savepowers": {"type": "boolean"},
                "keepopinfo": {"type": "boolean"},
                "fastmath2": {"type": "boolean"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_meas": {
        "title": "Prepare Measure Statement",
        "description": "Stage a schematic or netlist with a documented `.meas` statement (find/at, avg-family statistics, trig/targ intervals, Fourier components, or `.meas fra` frequency-response verification). Results are read post-simulation with `read_measures`.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "kind"],
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch` or netlist to stage.",
                },
                "kind": {
                    "type": "string",
                    "enum": ["find_at", "avg", "trig_targ", "fra", "four", "raw"],
                    "description": (
                        "Measurement family: find_at (value at time), avg (avg/max/min/pp/rms/integ "
                        "over an interval), trig_targ (interval between events), fra (frequency-"
                        "response check), four (Fourier component), raw (verbatim instruction)."
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Measure name used to look the result up via `read_measures`.",
                },
                "expression": {
                    "type": "string",
                    "description": "Waveform expression to measure (e.g. 'V(out)').",
                },
                "at": {"type": "string"},
                "statistic": {
                    "type": "string",
                    "enum": ["avg", "max", "min", "pp", "rms", "integ"],
                },
                "start": {"type": "string"},
                "stop": {"type": "string"},
                "trig": {"type": "string"},
                "targ": {"type": "string"},
                "frequency": {"type": "string"},
                "input_expression": {"type": "string"},
                "output_expression": {"type": "string"},
                "instruction": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_net": {
        "title": "Prepare Network Parameter Analysis",
        "description": "Stage a schematic or netlist with a documented `.net` directive for S/Y/Z/H one- or two-port parameter extraction alongside `.ac`. The input source must declare its impedance via `Rser`.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "input_source"],
            "properties": {
                "source_path": {"type": "string"},
                "input_source": {"type": "string"},
                "output_resistor": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_four": {
        "title": "Prepare Fourier Analysis",
        "description": "Stage a schematic or netlist with a documented `.four` THD directive; parse the results post-simulation with `read_fourier`.",
        "input_schema": {
            "type": "object",
            "required": ["source_path", "frequency", "expressions"],
            "properties": {
                "source_path": {"type": "string"},
                "frequency": {"type": "string"},
                "expressions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "harmonics": {"type": "integer", "minimum": 1},
                "periods": {"type": "integer", "minimum": 1},
                "output_path": {"type": "string"},
            },
        },
    },
    "prepare_monte_carlo": {
        "title": "Prepare Monte Carlo",
        "description": "Persist explicit Monte Carlo parameter samples for later copy-on-write execution.",
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
    },
    "list_plot_suggestions": {
        "title": "List Plot Suggestions",
        "description": "Inspect a schematic or netlist and surface `.plot`, `.print`, `.probe`, and `.abscissa` hints.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {"type": "string"},
                "netlist_output_path": {"type": "string"},
            },
        },
    },
    "summarize_tolerance_analysis": {
        "title": "Summarize Tolerance Analysis",
        "description": "Summarize Monte Carlo or worst-case target coverage and numeric `.meas` results from a persisted batch; measure refresh requires sibling run netlists and QPOST, or pass `refresh_measures=false` to use recorded `.meas` artifacts.",
        "input_schema": {
            "type": "object",
            "required": ["batch_path"],
            "properties": {
                "batch_path": {"type": "string"},
                "measures": {"type": "array", "items": {"type": "string"}},
                "refresh_measures": {"type": "boolean"},
            },
        },
    },
    "list_includes": {
        "title": "List Netlist Includes",
        "description": "List `.include`, `.inc`, and `.lib` directives reachable from one netlist.",
        "input_schema": {
            "type": "object",
            "required": ["netlist_path"],
            "properties": {"netlist_path": {"type": "string"}},
        },
    },
    "resolve_model_libraries": {
        "title": "Resolve Model Libraries",
        "description": "Resolve `.lib` model-library paths referenced by one netlist.",
        "input_schema": {
            "type": "object",
            "required": ["netlist_path"],
            "properties": {"netlist_path": {"type": "string"}},
        },
    },
    "add_library_include": {
        "title": "Add Library Include",
        "description": "Append one `.include`, `.inc`, or `.lib` directive to a netlist artifact.",
        "input_schema": {
            "type": "object",
            "required": ["netlist_path", "include_path"],
            "properties": {
                "netlist_path": {"type": "string"},
                "include_path": {"type": "string"},
                "kind": {"type": "string", "enum": ["include", "inc", "lib"]},
                "output_path": {"type": "string"},
                "relative_to_netlist": {"type": "boolean"},
            },
        },
    },
    "add_model": {
        "title": "Add Model Definition",
        "description": "Append one SPICE model definition block to a `.lib`, `.inc`, or netlist file.",
        "input_schema": {
            "type": "object",
            "required": ["target_path", "model_text"],
            "properties": {
                "target_path": {"type": "string"},
                "model_text": {"type": "string"},
                "output_path": {"type": "string"},
            },
        },
    },
    "run_simulation": {
        "title": "Run Simulation",
        "description": "Plan or run QSpice for a .qsch, .cir, or .net source path.",
        "input_schema": {
            "type": "object",
            "required": ["source_path"],
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qsch`, `.cir`, or `.net` to simulate.",
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "When true, report the planned command without executing QSpice.",
                },
                "timeout_s": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Per-run timeout in seconds; overrides the server default.",
                },
                "log_path": {"type": "string"},
                "raw_output_path": {"type": "string"},
                "netlist_output_path": {"type": "string"},
                "ascii_raw": {
                    "type": "boolean",
                    "description": "Emit ASCII `.qraw` instead of binary (larger but inspectable).",
                },
                "extra_switches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional QSPICE64 command-line switches.",
                },
                "run_id": {
                    "type": "string",
                    "description": "Optional caller-chosen id enabling `cancel_run`.",
                },
            },
        },
    },
    "cancel_run": {
        "title": "Cancel Run",
        "description": "Request cancellation of an in-flight run_simulation invocation by its run_id.",
        "input_schema": {
            "type": "object",
            "required": ["run_id"],
            "properties": {"run_id": {"type": "string"}},
        },
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
                "values": {"type": "array", "minItems": 1, "items": _SCALAR_VALUE},
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
                "models": {"type": "array", "minItems": 1, "items": {"type": "string"}},
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
    },
}
