In the name of God, the Most Gracious, the Most Merciful

# Sweep one design parameter

Use the schematic path, parameter name, and range supplied with the prompt. Sweep one design parameter and summarize the batch results instead of repeating single runs by hand.

1. Confirm the `.qsch` source; `generate_netlist` if the sibling netlist is stale.
2. Choose `run_value_sweep`, `run_param_sweep`, or `run_model_sweep` matching the parameter kind.
3. Use `parallelism=1` unless the workspace is isolated per run.
4. `summarize_batch` / `collect_batch_results`; read key waveforms for corner runs only.
5. Report the preferred value and any constraint violations.
