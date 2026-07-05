# Class-E ZVS DC-DC Converter -- reference recipe (Track B)

Zero-voltage-switching Class-E resonant DC-DC converter (single-switch resonant inverter plus rectifier).

**Source:** [PE-98](https://github.com/marcosalonsoelectronics/PE-98) by
J. Marcos Alonso -- "Design and Simulation of ZVS Class-E DC-DC Converters" -- file `2.- Class-E-dc-dc-converter.qsch` @ `b4ac83a`.
Adapted and redistributed with the author's permission.

## Files

- `class_e.qsch` -- Alonso's original QSpice schematic (source of truth).
- `class_e.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="class_e")` -- writes both files into the workspace.
2. `run_simulation(source_path="class_e.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.