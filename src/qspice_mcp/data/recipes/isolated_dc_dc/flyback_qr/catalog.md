# Quasi-Resonant Flyback Converter -- reference recipe (Track B)

Quasi-resonant (valley-switching) flyback converter with a behavioral ideal-diode rectifier and constant-on-time control. Steps 350 V down to roughly 5.7 V (turns ratio n=0.05).

**Source:** [PE-82](https://github.com/marcosalonsoelectronics/PE-82) by
J. Marcos Alonso -- "Quasi-Resonant Flyback Converter" -- file `2.- QR-Flyback - ideal-switch.qsch` @ `02be5df`.
Adapted and redistributed with the author's permission.

## Files

- `flyback_qr.qsch` -- Alonso's original QSpice schematic (source of truth).
- `flyback_qr.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="flyback_qr")` -- writes both files into the workspace.
2. `run_simulation(source_path="flyback_qr.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.
- Related topology block: `flyback_converter` (see `describe_topology_block`).

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.