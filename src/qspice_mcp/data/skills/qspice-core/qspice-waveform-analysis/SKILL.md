---
name: qspice-waveform-analysis
description: Inspect, derive, and measure QSpice waveform results after a simulation. Use when reading signals from a `.qraw`, comparing nodes, computing derived expressions like V(out)-V(in), measuring RMS/peak/gain/THD, or exporting traces for further analysis.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.0"
---

# QSpice: Waveform Analysis

A workflow for turning a completed `.qraw` result into answers: which signals
exist, what a derived quantity looks like, and what the scalar metrics are.

## When to use

- A simulation finished and you need to read or quantify the result.
- You need a *derived* signal (difference, product, ratio) the raw file does not
  store directly, e.g. `V(out)-V(in)` or instantaneous power `V(n1)*I(L1)`.
- You need scalar metrics (RMS, mean, peak-to-peak, gain) or a Fourier/noise
  summary.

## When NOT to use

- The run failed / produced no waveform → use `qspice-convergence-debugging`.
- You still need to author or simulate the circuit → `qspice-getting-started`.

## Workflow

1. **Enumerate.** `list_signals` (and `list_steps` for stepped/`.step` runs) to
   learn the exact, case-correct signal names. QSpice lowercases net names, so a
   node drawn as `VOUT` is read as `V(vout)`.
2. **Read a single trace.** `read_waveform` with a `signal` and optional
   `t_start`/`t_end`. Responses are budget-capped (2000 points); narrow the
   window instead of asking for everything.
3. **Derive across signals.** `evaluate_waveform_expression` with an arithmetic
   expression over signal tokens — `V(out)-V(in)`, `V(out)*I(L1)`,
   `2*V(fb)`. Only `+ - * / **`, parentheses, and numeric constants are allowed;
   all referenced signals must share one axis (same raw, step, window).
4. **Quantify.** `measure_waveform` for RMS/mean/max/min/peak-to-peak on one
   signal; `read_fourier` for `.four` THD summaries; `read_noise` for `.noise`
   integrated/spot output.
5. **Visualize / export.** `plot_waveforms` for a PNG preview; `export_waveform_csv`
   when downstream tooling needs the full series outside the MCP budget.

## Conventions

- Always `list_signals` first; never assume casing.
- Prefer `evaluate_waveform_expression` over manually reading two traces and
  subtracting by hand — it aligns axes and applies the budget.
- For complex AC data, pick an explicit `component` (`magnitude`/`phase`) rather
  than relying on `auto`.
- Confirm a result is physically sane with `measure_waveform`, not just that the
  read succeeded.
