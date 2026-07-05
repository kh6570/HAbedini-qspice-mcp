# LLC Resonant Converter -- reference recipe (Track B)

Full LLC series-resonant DC-DC converter (Lr-Cr-Lm tank plus rectifier) driven by a half-bridge with frequency control.

**Source:** [PE-119](https://github.com/marcosalonsoelectronics/PE-119) by
J. Marcos Alonso -- "Static and Dynamic Modelling of the LLC Resonant DC-DC Converter (I)" -- file `1.- LLC-converter-full.qsch` @ `a76824b`.
Adapted and redistributed with the author's permission.

## Files

- `llc_resonant.qsch` -- Alonso's original QSpice schematic (source of truth).
- `llc_resonant.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="llc_resonant")` -- writes both files into the workspace.
2. `run_simulation(source_path="llc_resonant.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.