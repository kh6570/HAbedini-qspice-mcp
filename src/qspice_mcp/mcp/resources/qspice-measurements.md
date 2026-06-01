# QSpice Measurement Guidance

Prefer bounded signal summaries and QPOST-backed `.meas` extraction for compact
responses. `read_waveform` JSON responses are capped at 2000 points and 64000
bytes; use `plot_waveforms`, `export_waveform_csv`, or `export_derived_raw`
when you need larger artifacts.