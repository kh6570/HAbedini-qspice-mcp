# Current-Fed Push-Pull Resonant Converter -- reference recipe (Track B)

Current-fed push-pull resonant DC-DC converter (100 kHz) with a resonant
transformer tank and behavioral ideal-diode output rectifier. Boosts 12 V to
roughly 24 V into a 5.76 ohm load.

**Source:** [PE-93](https://github.com/marcosalonsoelectronics/PE-93) by
J. Marcos Alonso -- "Current-fed push-pull resonant DC-DC converter" -- file
`1.- Current-fed-push-pull-resonant-dc-dc-converter.qsch` @ `5bf38f2`.
Adapted and redistributed with the author's permission.

## Files

- `push_pull_resonant.qsch` -- Alonso's original QSpice schematic (source of truth).
- `push_pull_resonant.cir` -- self-contained netlist (behavioral library inlined),
  with one added `.options cshunt=1e-12` line for convergence.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="push_pull_resonant")` -- writes both files.
2. `run_simulation(source_path="push_pull_resonant.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw`; `V(out)` settles near 24 V.
- Related topology block: `push_pull_converter` (see `describe_topology_block`).

> Note: the bundled `.cir` adds a single `.options cshunt=1e-12` (a 1 pF shunt at
> every node) so the ideal-switch resonant tank converges; without it QSpice aborts
> mid-run with `Timestep too small`. Re-netlisting the `.qsch` yourself requires
> QSpice/QUX with Alonso's `.qsym` library on the symbol path.
