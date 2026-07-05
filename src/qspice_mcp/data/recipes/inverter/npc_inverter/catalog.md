# Three-Level NPC Inverter -- reference recipe (Track B)

Three-level neutral-point-clamped (NPC) inverter with sinusoidal PWM (amplitude index 0.8, frequency ratio 20).

**Source:** [PE-96](https://github.com/marcosalonsoelectronics/PE-96) by
J. Marcos Alonso -- "Three-level Neutral Point Clamped (NPC) Inverter" -- file `1.- NPC-inverter-ma08-mf20.qsch` @ `90dd94e`.
Adapted and redistributed with the author's permission.

## Files

- `npc_inverter.qsch` -- Alonso's original QSpice schematic (source of truth).
- `npc_inverter.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="npc_inverter")` -- writes both files into the workspace.
2. `run_simulation(source_path="npc_inverter.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.