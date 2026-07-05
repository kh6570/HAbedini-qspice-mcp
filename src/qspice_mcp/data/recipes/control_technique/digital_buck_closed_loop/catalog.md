# Digital Voltage-Mode Buck (Closed Loop, C++ C-block) -- reference recipe (Track B)

Synchronous buck regulated by a digital voltage-mode controller implemented as a
QSpice C++ C-block (DPWMCL): sample-and-hold, discrete PI compensator, and digital
PWM. Regulates the output to about 5 V.

**Source:** [Qspice-3](https://github.com/marcosalonsoelectronics/Qspice-3) by
J. Marcos Alonso -- file `1.- buck-digital-control-closed-loop.qsch` @ `7876631`.
Adapted and redistributed with the author's permission.

## Files

- `digital_buck_closed_loop.qsch` -- Alonso's original QSpice schematic (source of truth).
- `dpwmcl.cpp` -- Alonso's C-block source; compiles to `dpwmcl.dll` (the `DPWMCL` device).
- `digital_buck_closed_loop.cir` -- self-contained QUX netlist that references `DPWMCL`.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="digital_buck_closed_loop")` -- writes all files.
2. `build_dll_device(source_path="dpwmcl.cpp")` -- compiles `dpwmcl.dll` beside the netlist.
3. `run_simulation(source_path="digital_buck_closed_loop.cir")` -- runs the netlist.
4. `measure_waveform` on `V(out)` in the produced `.qraw`; it settles near 5 V.
- Related topology block: `buck_converter` (see `describe_topology_block`).

> Note: the `.cir` references QSpice's built-in `NMOS.txt`/`Diode.txt` device models
> by their default install path (`C:\Program Files\QSPICE\`); a standard QSpice
> install resolves them. Keep `dpwmcl.cpp`'s filename so the DLL matches the `DPWMCL`
> device.
