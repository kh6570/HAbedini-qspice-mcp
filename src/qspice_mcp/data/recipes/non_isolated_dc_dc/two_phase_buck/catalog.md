# Two-Phase (Multiphase) Buck Converter -- reference recipe (Track B)

Interleaved two-phase synchronous buck converter demonstrating multiphase current sharing and output ripple cancellation.

**Source:** [PE-103](https://github.com/marcosalonsoelectronics/PE-103) by
J. Marcos Alonso -- "Introduction to Multiphase Buck DC-DC Converters" -- file `3.- Two-phase-buck-converter.qsch` @ `a5b6c91`.
Adapted and redistributed with the author's permission.

## Files

- `two_phase_buck.qsch` -- Alonso's original QSpice schematic (source of truth).
- `two_phase_buck.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="two_phase_buck")` -- writes both files into the workspace.
2. `run_simulation(source_path="two_phase_buck.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.
- Related topology block: `buck_converter` (see `describe_topology_block`).

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.