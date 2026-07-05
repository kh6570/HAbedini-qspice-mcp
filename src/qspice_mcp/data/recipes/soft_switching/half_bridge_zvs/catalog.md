# Half-Bridge ZVS Leg -- reference recipe (Track B)

Half-bridge MOSFET leg with an L-R load illustrating zero-voltage switching and the role of dead-time.

**Source:** [PE-79-80](https://github.com/marcosalonsoelectronics/PE-79-80) by
J. Marcos Alonso -- "Understanding Zero Voltage Switching in Half-Bridge Converters" -- file `1.- Half-bridge-LR-mosfets.qsch` @ `d89487c`.
Adapted and redistributed with the author's permission.

## Files

- `half_bridge_zvs.qsch` -- Alonso's original QSpice schematic (source of truth).
- `half_bridge_zvs.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="half_bridge_zvs")` -- writes both files into the workspace.
2. `run_simulation(source_path="half_bridge_zvs.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.