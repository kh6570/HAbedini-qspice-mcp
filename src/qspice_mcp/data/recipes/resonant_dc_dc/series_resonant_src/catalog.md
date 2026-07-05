# Series Resonant Converter (SRC) -- reference recipe (Track B)

Full series-resonant DC-DC converter with an L-C resonant tank and full-bridge inverter drive.

**Source:** [PE-110](https://github.com/marcosalonsoelectronics/PE-110) by
J. Marcos Alonso -- "Static and Dynamic Modelling of the Series Resonant DC-DC Converter (SRC) (I)" -- file `1.- SRC-converter-full.qsch` @ `9aa0368`.
Adapted and redistributed with the author's permission.

## Files

- `series_resonant_src.qsch` -- Alonso's original QSpice schematic (source of truth).
- `series_resonant_src.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="series_resonant_src")` -- writes both files into the workspace.
2. `run_simulation(source_path="series_resonant_src.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.