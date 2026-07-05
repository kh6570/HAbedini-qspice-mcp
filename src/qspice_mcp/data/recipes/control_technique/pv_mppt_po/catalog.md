# PV Buck with Perturb-and-Observe MPPT (C++ C-block) -- reference recipe (Track B)

Photovoltaic buck stage with a Perturb-and-Observe maximum-power-point tracker
implemented as a QSpice C++ C-block (Controller20), driving a behavioral PV-module
source model. Demonstrates MPPT convergence over a long (120 ms) transient.

**Source:** [PE-95](https://github.com/marcosalonsoelectronics/PE-95) by
J. Marcos Alonso -- file `2.- PV-Buck-converter-PO.qsch` @ `1d51940`.
Adapted and redistributed with the author's permission.

## Files

- `pv_mppt_po.qsch` -- Alonso's original QSpice schematic (source of truth).
- `controller20.cpp` -- Alonso's C-block MPPT source; compiles to `controller20.dll` (the `Controller20` device).
- `pv_mppt_po.cir` -- self-contained QUX netlist (behavioral PV-module + current-sense inlined) referencing `Controller20`.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="pv_mppt_po")` -- writes all files.
2. `build_dll_device(source_path="controller20.cpp")` -- compiles `controller20.dll` beside the netlist.
3. `run_simulation(source_path="pv_mppt_po.cir")` -- runs the netlist (120 ms; expect a long run and a large `.qraw`).
4. `measure_waveform` on the PV terminal power / `V(out)` to watch the P&O tracker settle.
- Related topology block: `buck_converter` (see `describe_topology_block`).

> Note: the 120 ms transient produces a very large `.qraw` (order of a gigabyte);
> use `read_waveform`/`measure_waveform` with a time window and `max_points`.
> Keep `controller20.cpp`'s filename so the DLL matches the `Controller20` device.
