In the name of God, the Most Gracious, the Most Merciful

# Waveform workflow

1. **Enumerate.** `list_signals` (and `list_steps` for stepped/`.step` runs) to learn the exact, case-correct signal names. QSpice lowercases net names, so a node drawn as `VOUT` is read as `V(vout)`.
2. **Read a single trace.** `read_waveform` with a `signal` and optional `t_start`/`t_end`. Responses are budget-capped (2000 points); narrow the window instead of asking for everything.
3. **Derive across signals.** `evaluate_waveform_expression` with an arithmetic expression over signal tokens — `V(out)-V(in)`, `V(out)*I(L1)`, `2*V(fb)`. Only `+ - * / **`, parentheses, and numeric constants are allowed; all referenced signals must share one axis (same raw, step, window).
4. **Quantify.** `measure_waveform` for RMS/mean/max/min/peak-to-peak on one signal; `read_noise` for `.noise` integrated/spot output.
5. **Harmonics and distortion.** Stage `.four` with `prepare_four`, re-run, then `read_fourier` for the harmonic table — or skip the directive entirely and use `compute_thd` (post-processing FFT THD on any periodic trace) and `export_fft_spectrum` for a full spectrum CSV.
6. **Frequency response.** `measure_bode_response` extracts gain/phase versus frequency from an AC or `.bode` result in one call.
7. **Log-side measures.** `prepare_meas` stages `.meas` directives (`find_at`/`avg`/`trig_targ`/`fra`/`four`); after the run, `list_measures` enumerates the QPOST-derived blocks and `read_measures` returns their values with optional step filtering.
8. **Visualize / export.** `plot_waveforms` for a PNG preview; `export_waveform_csv` when downstream tooling needs the full series outside the MCP budget.

## Conventions

- Always `list_signals` first; never assume casing.
- Prefer `evaluate_waveform_expression` over manually reading two traces and subtracting by hand — it aligns axes and applies the budget.
- For complex AC data, pick an explicit `component` (`magnitude`/`phase`) rather than relying on `auto`.
- Confirm a result is physically sane with `measure_waveform`, not just that the read succeeded.
