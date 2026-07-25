# QSpice Measurement Guidance

Prefer bounded signal summaries and QPOST-backed `.meas` extraction for compact
responses. `read_waveform` JSON responses are capped at 2000 points and 64000
bytes; use `plot_waveforms`, `export_waveform_csv`, or `export_derived_raw`
when you need larger artifacts.

## Scalar answers without raw samples

- `measure_waveform` — RMS/mean/max/min/peak-to-peak on one signal.
- `evaluate_waveform_expression` — derived traces (`V(out)-V(in)`, `V(n1)*I(L1)`)
  with the same budget applied.

## `.meas` directives (log-side measures)

- `prepare_meas` stages `.meas` directives from templates
  (`find_at`, `avg`, `trig_targ`, `fra`, `four`) plus a validated `raw` escape
  hatch, so measures live in the staged artifact instead of ad-hoc text.
- After the run, `list_measures` enumerates the QPOST-derived measurement blocks
  for a `.log`, and `read_measures` returns values with optional `.step`
  filtering. `read_log` includes the same measures inline with the log excerpt.
- These tools refresh the `.meas` sidecar through QPOST by default
  (`refresh_measures=true`), so they write next to the log.

## `.meas fra` — the trustworthy frequency check

`.meas <name> fra <freq> <input> <output>` is the most reliable frequency-domain
measurement QSpice offers. Use it (via `prepare_meas(kind="fra")`) to
independently verify crossover points reported by `.bode` /
`measure_stability_margins`, which can carry numerical artifacts.
