# Voltage-Fed Push-Pull Resonant Inverter -- reference recipe (Track B)

Voltage-fed push-pull resonant inverter (100 kHz) driving a series-resonant tank
and transformer. Produces a roughly 68 V-RMS sinusoidal output (about +/-84 V peak)
across a 100 ohm load.

**Source:** [PE-94](https://github.com/marcosalonsoelectronics/PE-94) by
J. Marcos Alonso -- "Voltage-fed push-pull resonant inverter" -- file
`1.- Voltage-fed-push-pull-resonant-inverter.qsch` @ `2d8714c`.
Adapted and redistributed with the author's permission.

## Files

- `voltage_fed_push_pull.qsch` -- Alonso's original QSpice schematic (source of truth).
- `voltage_fed_push_pull.cir` -- self-contained netlist (behavioral library inlined),
  ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="voltage_fed_push_pull")` -- writes both files.
2. `run_simulation(source_path="voltage_fed_push_pull.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw`; `V(out)` is a ~68 V-RMS sinusoid.
- Related topology block: `push_pull_converter` (see `describe_topology_block`).

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice/QUX with Alonso's `.qsym` component library on the symbol path; the bundled
> `.cir` already has those subcircuits inlined.
