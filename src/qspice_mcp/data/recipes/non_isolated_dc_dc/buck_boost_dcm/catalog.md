# Buck-Boost Converter (DCM) -- reference recipe (Track B)

Inverting buck-boost converter running in discontinuous conduction mode using a linear MOSFET model.

**Source:** [PE-90](https://github.com/marcosalonsoelectronics/PE-90) by
J. Marcos Alonso -- "Buck-Boost Converter in DCM" -- file `1.- Buck-boost-DCM-Mosfet-linear-model.qsch` @ `8c90fb5`.
Adapted and redistributed with the author's permission.

## Files

- `buck_boost_dcm.qsch` -- Alonso's original QSpice schematic (source of truth).
- `buck_boost_dcm.cir` -- self-contained netlist (his behavioral component library embedded
  by QSpice/QUX), ready to simulate without any external symbol files.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="buck_boost_dcm")` -- writes both files into the workspace.
2. `run_simulation(source_path="buck_boost_dcm.cir")` -- runs the ready-to-run netlist.
3. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect results.
- Related topology block: `buck_boost_converter` (see `describe_topology_block`).

> Note: simulate the bundled `.cir`. Re-netlisting the `.qsch` yourself requires
> QSpice's GUI/QUX with Alonso's `.qsym` component library on the symbol path; the
> bundled `.cir` already has those subcircuits inlined.