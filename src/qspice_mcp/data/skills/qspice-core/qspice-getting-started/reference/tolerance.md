In the name of God, the Most Gracious, the Most Merciful

# Tolerance analysis

Use the schematic path, metric expression, and Monte Carlo run count supplied with the prompt. Quantify how component tolerances affect that design metric.

1. `inspect_schematic` to identify tolerance-bearing components (R/L/C values, reference sources).
2. `prepare_monte_carlo` with per-component tolerances and the run count; `run_monte_carlo` on the staged plan.
3. `prepare_worst_case` with the same tolerances; `run_worst_case` for the deterministic corner extremes.
4. `summarize_tolerance_analysis` over both batches for the metric: mean, sigma, min/max, and which corner produced each extreme.
5. Report the tolerance-driven spread against the design target and flag components whose tolerance dominates the variation.
