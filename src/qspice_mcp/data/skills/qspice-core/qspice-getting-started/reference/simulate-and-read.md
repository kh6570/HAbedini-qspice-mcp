In the name of God, the Most Gracious, the Most Merciful

# Simulate and read

## Simulate

1. `generate_netlist` — resolve/stage the derived netlist (refreshes a stale sibling `.net` when the schematic is newer). Often optional — `run_simulation` can take a `.qsch` directly.
2. `prepare_*` staging tools — optional staging that writes a sibling file (for example `filter-tran.qsch`). The family covers every documented analysis: `prepare_transient`, `prepare_ac`, `prepare_dc_sweep`, `prepare_noise`, `prepare_bode_analysis`, `prepare_loop_gain_analysis`, `prepare_transfer_function`, `prepare_sensitivity`, `prepare_temperature_sweep`, `prepare_op`, `prepare_four`, `prepare_net`, plus output/bookkeeping staging (`prepare_save`, `prepare_options`, `prepare_meas`). Prefer these over hand-written `add_instruction` lines. **Simulate `output_path`; edit layout on `source_path`.** After any placement change on the source, call `prepare_*` again so the sibling matches.
3. `run_simulation` — execute from a `.qsch`, `.cir`, or `.net`. This is long-running; expect a wait for transient analyses.

**Layout verification before done:** `read_component` on every ref — reject duplicate `(position_x, position_y)` pairs and fix with `suggest_component_placement` / explicit coordinates before staging or sim.

For design exploration use the sweep tools instead of repeated single runs: `run_value_sweep`, `run_param_sweep`, `run_model_sweep`, `run_monte_carlo`, `run_worst_case`. (These currently require a `.qsch` source.) For tolerance studies, open `tolerance.md`. For one parameter range, open `sweep.md`.

## Read results

- `read_log` — concise diagnostic excerpt + optional measures. **Always read the log after a run** to confirm it converged and completed.
- `list_signals` — enumerate signals in the `.qraw`.
- `measure_waveform` — scalar measurements (preferred).
- `read_waveform` — bounded samples when you need the actual trace.
- `plot_waveforms` — generate a plot artifact for selected signals.

## The canonical loop

```
describe_server_capabilities        # once, when unsure of environment
list/describe/materialize recipe    # or author from scratch (Track A)
inspect_schematic                   # confirm structure
run_simulation                      # execute
read_log                            # verify convergence/completion
list_signals → measure_waveform     # extract the answer
```

## Run and measure

Use the schematic path and signal list supplied with the prompt.

1. `generate_netlist` if the source is `.qsch`.
2. `run_simulation` on the derived `.net`/`.cir`.
3. `list_signals`, then `read_waveform` with budgets respected.
4. `measure_waveform` for min/max/RMS on the requested signals.
5. Summarize pass/fail against the expected operating point or ripple targets.
