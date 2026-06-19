"""Waveform tool metadata."""

from __future__ import annotations

from .common import _COMPONENT, _STEP_FILTERS, _ann

WAVEFORM_TOOL_METADATA: dict[str, dict[str, object]] = {
    "list_steps": {
        "title": "List Steps",
        "description": (
            "Enumerate available simulation steps and their variable assignments without "
            "returning waveform samples; sibling `.log` metadata produces the richest step labels."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {"raw_path": {"type": "string"}},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "list_signals": {
        "title": "List Signals",
        "description": (
            "List available waveform signals without returning samples; compatible no-backend "
            "reads are limited to the supported raw fallback subset."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {
                "raw_path": {"type": "string"},
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_device_operating_points": {
        "title": "Read Device Operating Points",
        "description": (
            "Read device operating-point currents, powers, and node voltages from one "
            "Operating Point `.qraw`; requires a sibling `.net`/`.cir` or `netlist_path`, "
            "and current/power coverage is richest when the run used `.option KEEPOPINFO` "
            "plus `.option SAVEPOWERS`."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {
                "raw_path": {"type": "string"},
                "netlist_path": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "filter_device_operating_points": {
        "title": "Filter Device Operating Points",
        "description": (
            "Filter one Operating Point device catalog by family, model, reference, and metric "
            "presence; the same raw/netlist preconditions as `read_device_operating_points` apply."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "summarize_device_operating_points": {
        "title": "Summarize Device Operating Points",
        "description": (
            "Return compact family-level and extremum summaries for one Operating Point `.qraw`; "
            "requires the same sibling netlist and operating-point trace preconditions as the "
            "full device read."
        ),
        "input_schema": {
            "type": "object",
            "required": ["raw_path"],
            "properties": {
                "raw_path": {"type": "string"},
                "netlist_path": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_waveform": {
        "title": "Read Waveform",
        "description": (
            "Return bounded waveform samples for a signal. JSON responses are capped at 2000 "
            "points and 64000 bytes; use `plot_waveforms`, `export_waveform_csv`, or "
            "`export_derived_raw` for larger outputs."
        ),
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
                "max_points": {"type": "integer", "minimum": 3},
                "max_bytes": {"type": "integer", "minimum": 1024},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "measure_waveform": {
        "title": "Measure Waveform",
        "description": "Compute scalar measurements from one or more waveforms.",
        "input_schema": {
            "type": "object",
            "required": ["raw_path", "signal", "operation"],
            "properties": {
                "raw_path": {"type": "string"},
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
                "step": {"type": "integer", "minimum": 0},
                "step_filters": _STEP_FILTERS,
                "component": _COMPONENT,
                "t_start": {"type": "number"},
                "t_end": {"type": "number"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "measure_bode_response": {
        "title": "Measure Bode Response",
        "description": (
            "Sample magnitude and phase from one frequency-domain waveform "
            "trace at requested frequencies."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "measure_stability_margins": {
        "title": "Measure Stability Margins",
        "description": (
            "Compute crossover frequency, phase margin, and gain margin from one "
            "loop-gain frequency-domain waveform trace."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "measure_step_response": {
        "title": "Measure Step Response",
        "description": (
            "Compute rise time, delay, overshoot, and settling time from one "
            "transient waveform trace."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "measure_efficiency": {
        "title": "Measure Efficiency",
        "description": (
            "Compute average input power, output power, and Pout/Pin efficiency "
            "from transient power traces such as SAVEPOWERS `p(...)` signals."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "compute_thd": {
        "title": "Compute THD",
        "description": (
            "Estimate total harmonic distortion over a trailing integer-cycle waveform window."
        ),
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
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "export_fft_spectrum": {
        "title": "Export FFT Spectrum",
        "description": (
            "Resample one time-domain waveform window and export its "
            "single-sided FFT spectrum as CSV."
        ),
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
        "annotations": _ann(idempotent=True),
    },
    "plot_waveforms": {
        "title": "Plot Waveforms",
        "description": (
            "Generate a derived plot artifact for one or more waveforms, avoiding the bounded "
            "`read_waveform` JSON ceiling when you need larger visual outputs."
        ),
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
        "annotations": _ann(idempotent=True),
    },
    "read_log": {
        "title": "Read Simulation Log",
        "description": (
            "Return a concise log excerpt and optionally materialize QPOST-based measures; "
            "refreshing measures requires a sibling `.net`/`.cir` plus a configured `QPOST.exe`."
        ),
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {
                "log_path": {"type": "string"},
                "max_lines": {"type": "integer", "minimum": 0},
                "include_measures": {"type": "boolean"},
                "refresh_measures": {"type": "boolean"},
                "meas_path": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "list_measures": {
        "title": "List Measures",
        "description": (
            "Enumerate QPOST-derived measurement blocks for one simulation log; set "
            "`refresh_measures=false` to reuse an existing `.meas` file when QPOST or the sibling "
            "netlist is unavailable."
        ),
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {
                "log_path": {"type": "string"},
                "refresh_measures": {"type": "boolean"},
                "meas_path": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_measures": {
        "title": "Read Measures",
        "description": (
            "Return QPOST-derived measurement values with optional measure and step filtering; "
            "set `refresh_measures=false` to read a recorded `.meas` file without rerunning QPOST."
        ),
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
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_fourier": {
        "title": "Read Fourier Analysis",
        "description": (
            "Parse native QSpice `.four` Fourier summaries from a simulation `.log` file. "
            "Distinct from recomputed FFT tools such as `compute_thd`."
        ),
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {"log_path": {"type": "string"}},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "read_noise": {
        "title": "Read Noise Analysis",
        "description": (
            "Parse integrated and spot `.noise` summary lines from a simulation `.log` file."
        ),
        "input_schema": {
            "type": "object",
            "required": ["log_path"],
            "properties": {"log_path": {"type": "string"}},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
}


__all__ = ["WAVEFORM_TOOL_METADATA"]
