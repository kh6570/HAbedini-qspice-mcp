# Digital Current-Mode Buck (Closed Loop, C++ C-block) -- reference recipe (Track B)

Synchronous buck under digital peak-current-mode control implemented as a QSpice
C++ C-block (Controller2): per-cycle current sampling, slope/PI compensation, and
digital PWM. Regulates the output to about 5 V.

**Source:** [PE-66](https://github.com/marcosalonsoelectronics/PE-66) by
J. Marcos Alonso -- file `3.- Current-mode-digital-closed-loop.qsch` @ `76c66ee`.
Adapted and redistributed with the author's permission.

## Files

- `digital_current_mode_buck.qsch` -- Alonso's original QSpice schematic (source of truth).
- `controller2.cpp` -- Alonso's C-block source; compiles to `controller2.dll` (the `Controller2` device).
- `digital_current_mode_buck.cir` -- self-contained QUX netlist that references `Controller2`.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="digital_current_mode_buck")` -- writes all files.
2. `build_dll_device(source_path="controller2.cpp")` -- compiles `controller2.dll` beside the netlist.
3. `run_simulation(source_path="digital_current_mode_buck.cir")` -- runs the netlist.
4. `measure_waveform` on `V(out)` in the produced `.qraw`; it settles near 5 V.
- Related topology block: `buck_converter` (see `describe_topology_block`).

> Note: the `.cir` references QSpice's built-in `NMOS.txt`/`Diode.txt` device models
> by their default install path (`C:\Program Files\QSPICE\`); a standard QSpice
> install resolves them. Keep `controller2.cpp`'s filename so the DLL matches the
> `Controller2` device.
