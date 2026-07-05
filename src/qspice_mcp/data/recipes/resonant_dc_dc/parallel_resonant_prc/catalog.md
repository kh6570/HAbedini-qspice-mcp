# Parallel Resonant Converter (PRC) -- reference recipe (Track B)

Full parallel-resonant DC-DC converter with the load reflected across the resonant capacitor.

**Source:** [PE-113](https://github.com/marcosalonsoelectronics/PE-113) by
J. Marcos Alonso -- "Static and Dynamic Modelling of the Parallel Resonant DC-DC Converter (PRC) (I)" -- file `1.- PRC-converter-full.qsch` @ `43cb6dc`.
Adapted and redistributed with the author's permission.

## Files

- `parallel_resonant_prc.qsch` -- Alonso's original QSpice schematic (source of truth).
- `parallel_resonant_prc.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="parallel_resonant_prc")` -- writes both files into the workspace.
2. `run_simulation(source_path="parallel_resonant_prc.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.