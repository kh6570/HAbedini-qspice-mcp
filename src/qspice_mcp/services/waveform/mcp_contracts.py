from qspice_mcp.services._internals.mcp_schema_common import (
    _COMPONENT,
    _STEP_FILTERS,
)

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "evaluate_waveform_expression": {
        "title": "Evaluate Waveform Expression",
        "description": "Evaluate an arithmetic expression over one or more `.qraw` signals (for example `V(out)-V(in)` or `V(out)*I(L1)`) and return a budgeted result series. Supports signal tokens, numeric constants, parentheses, and the + - * / ** operators; all referenced signals must share one axis.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "expression"],
            "properties": {
                "raw_path": {"type": "string"},
                "expression": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
                "max_points": {"type": "integer", "minimum": 1},
                "max_bytes": {"type": "integer", "minimum": 1},
            },
        },
    },
    "list_steps": {
        "title": "List Steps",
        "description": "Enumerate available simulation steps and their variable assignments without returning waveform samples; sibling `.log` metadata produces the richest step labels.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {"raw_path": {"type": "string"}},
        },
    },
    "list_signals": {
        "title": "List Signals",
        "description": "List available waveform signals without returning samples; compatible no-backend reads are limited to the supported raw fallback subset.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {
                "raw_path": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "name_filter": {
                    "type": "string",
                    "description": "Case-insensitive glob restricting rows, e.g. 'V(*)' or 'I(L?)'.",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Bound the returned signal rows; signals_truncated flags cuts.",
                },
            },
        },
    },
    "read_device_operating_points": {
        "title": "Read Device Operating Points",
        "description": "Read device operating-point currents, powers, and node voltages from one Operating Point `.qraw`; requires a sibling `.net`/`.cir` or `netlist_path`, and current/power coverage is richest when the run used `.option KEEPOPINFO` plus `.option SAVEPOWERS`.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {"raw_path": {"type": "string"}, "netlist_path": {"type": "string"}},
        },
    },
    "filter_device_operating_points": {
        "title": "Filter Device Operating Points",
        "description": "Filter one Operating Point device catalog by family, model, reference, and metric presence; the same raw/netlist preconditions as `read_device_operating_points` apply.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {
                "raw_path": {"type": "string"},
                "netlist_path": {"type": "string"},
                "families": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "models": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "references": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "reference_pattern": {"type": "string"},
                "metric_names": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            },
        },
    },
    "summarize_device_operating_points": {
        "title": "Summarize Device Operating Points",
        "description": "Return compact family-level and extremum summaries for one Operating Point `.qraw`; requires the same sibling netlist and operating-point trace preconditions as the full device read.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {"raw_path": {"type": "string"}, "netlist_path": {"type": "string"}},
        },
    },
    "read_waveform": {
        "title": "Read Waveform",
        "description": "Return bounded waveform samples for a signal. JSON responses are capped at 2000 points and 64000 bytes; use `plot_waveforms`, `export_waveform_csv`, or `export_derived_raw` for larger outputs.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal"],
            "properties": {
                "raw_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qraw` produced by a simulation run.",
                },
                "signal": {
                    "type": "string",
                    "description": "Trace name or expression, e.g. 'V(out)' or 'I(L1)'.",
                },
                "step": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based step index for stepped (.step) runs.",
                },
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {
                    "type": "number",
                    "description": "Optional window start on the sweep axis (seconds or Hz).",
                },
                "t_end": {
                    "type": "number",
                    "description": "Optional window end on the sweep axis (seconds or Hz).",
                },
                "max_points": {
                    "type": "integer",
                    "minimum": 3,
                    "description": "Downsample budget; hard cap 2000 points.",
                },
                "max_bytes": {"type": "integer", "minimum": 1024},
            },
        },
    },
    "measure_waveform": {
        "title": "Measure Waveform",
        "description": "Compute scalar measurements from one or more waveforms.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal", "operation"],
            "properties": {
                "raw_path": {
                    "type": "string",
                    "description": "Workspace-relative `.qraw` produced by a simulation run.",
                },
                "signal": {
                    "type": "string",
                    "description": "Trace name or expression, e.g. 'V(out)' or 'I(L1)'.",
                },
                "operation": {
                    "type": "string",
                    "description": "Scalar reduction applied over the (optionally windowed) trace.",
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
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
        },
    },
    "measure_bode_response": {
        "title": "Measure Bode Response",
        "description": "Sample magnitude and phase from one frequency-domain waveform trace at requested frequencies.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal", "frequencies_hz"],
            "properties": {
                "raw_path": {"type": "string"},
                "signal": {"type": "string"},
                "frequencies_hz": {"type": "array", "items": {"type": "number"}, "minItems": 1},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
            },
        },
    },
    "measure_stability_margins": {
        "title": "Measure Stability Margins",
        "description": "Compute crossover frequency, phase margin, and gain margin from one loop-gain frequency-domain waveform trace.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal"],
            "properties": {
                "raw_path": {"type": "string"},
                "signal": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
            },
        },
    },
    "measure_step_response": {
        "title": "Measure Step Response",
        "description": "Compute rise time, delay, overshoot, and settling time from one transient waveform trace.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal"],
            "properties": {
                "raw_path": {"type": "string"},
                "signal": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
                "initial_value": {"type": "number"},
                "final_value": {"type": "number"},
                "lower_pct": {"type": "number", "minimum": 0, "maximum": 100},
                "upper_pct": {"type": "number", "minimum": 0, "maximum": 100},
                "settling_band_pct": {"type": "number", "exclusiveMinimum": 0},
            },
        },
    },
    "measure_efficiency": {
        "title": "Measure Efficiency",
        "description": "Compute average input power, output power, and Pout/Pin efficiency from transient power traces such as SAVEPOWERS `p(...)` signals.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "input_power_signal", "output_power_signal"],
            "properties": {
                "raw_path": {"type": "string"},
                "input_power_signal": {"type": "string"},
                "output_power_signal": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
        },
    },
    "compute_thd": {
        "title": "Compute THD",
        "description": "Estimate total harmonic distortion over a trailing integer-cycle waveform window.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal", "fundamental_hz"],
            "properties": {
                "raw_path": {"type": "string"},
                "signal": {"type": "string"},
                "fundamental_hz": {"type": "number", "exclusiveMinimum": 0},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "periods": {"type": "integer", "minimum": 1},
                "harmonics": {"type": "integer", "minimum": 2},
                "t_end": {"type": "number"},
                "samples_per_cycle": {"type": "integer", "minimum": 16},
            },
        },
    },
    "export_fft_spectrum": {
        "title": "Export FFT Spectrum",
        "description": "Resample one time-domain waveform window and export its single-sided FFT spectrum as CSV.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal"],
            "properties": {
                "raw_path": {"type": "string"},
                "signal": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
                "sample_count": {"type": "integer", "minimum": 2},
                "max_frequency_hz": {"type": "number", "exclusiveMinimum": 0},
                "output_path": {"type": "string"},
            },
        },
    },
    "plot_waveforms": {
        "title": "Plot Waveforms",
        "description": "Generate a derived plot artifact for one or more waveforms, avoiding the bounded `read_waveform` JSON ceiling when you need larger visual outputs.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signals"],
            "properties": {
                "raw_path": {"type": "string"},
                "signals": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
                "max_points": {"type": "integer", "minimum": 3},
                "max_bytes": {"type": "integer", "minimum": 1024},
                "output_path": {"type": "string"},
                "fmt": {"type": "string", "enum": ["png", "svg"]},
                "title": {"type": "string"},
            },
        },
    },
    "read_log": {
        "title": "Read Simulation Log",
        "description": "Return a concise log excerpt and optionally materialize QPOST-based measures; refreshing measures requires a sibling `.net`/`.cir` plus a configured `QPOST.exe`.",
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {
                "log_path": {
                    "type": "string",
                    "description": "Workspace-relative `.log` produced by a simulation run.",
                },
                "max_lines": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Cap on returned log lines (tail-biased excerpt).",
                },
                "include_measures": {
                    "type": "boolean",
                    "description": "Also return parsed measurement blocks.",
                },
                "refresh_measures": {
                    "type": "boolean",
                    "description": "Rerun QPOST to regenerate the `.meas` sidecar (default true; writes a file).",
                },
                "meas_path": {
                    "type": "string",
                    "description": "Optional explicit `.meas` path when not the sibling default.",
                },
                "max_measure_rows": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Bound the rows returned per measurement block; measure_rows_truncated flags cuts.",
                },
            },
        },
    },
    "list_measures": {
        "title": "List Measures",
        "description": "Enumerate QPOST-derived measurement blocks for one simulation log; set `refresh_measures=false` to reuse an existing `.meas` file when QPOST or the sibling netlist is unavailable.",
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {
                "log_path": {"type": "string"},
                "refresh_measures": {"type": "boolean"},
                "meas_path": {"type": "string"},
            },
        },
    },
    "read_measures": {
        "title": "Read Measures",
        "description": "Return QPOST-derived measurement values with optional measure and step filtering; set `refresh_measures=false` to read a recorded `.meas` file without rerunning QPOST.",
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {
                "log_path": {"type": "string"},
                "measures": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "refresh_measures": {"type": "boolean"},
                "meas_path": {"type": "string"},
                "max_measure_rows": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Bound the rows returned per measurement block after step filtering; measure_rows_truncated flags cuts.",
                },
            },
        },
    },
    "read_fourier": {
        "title": "Read Fourier Analysis",
        "description": "Parse native QSpice `.four` Fourier summaries from a simulation `.log` file. Distinct from recomputed FFT tools such as `compute_thd`.",
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {"log_path": {"type": "string"}},
        },
    },
    "read_noise": {
        "title": "Read Noise Analysis",
        "description": "Parse integrated and spot `.noise` summary lines from a simulation `.log` file.",
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {"log_path": {"type": "string"}},
        },
    },
}
