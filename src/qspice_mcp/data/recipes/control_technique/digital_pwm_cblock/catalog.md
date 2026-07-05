# Digital PWM Generator (C++ C-block) -- reference recipe (Track B)

Minimal digital PWM generator implemented as a QSpice C++ C-block (DPWM): a
sampled duty-cycle input produces a switching gate waveform. The building block
behind Alonso's digital-control converter demos.

**Source:** [Qspice-2](https://github.com/marcosalonsoelectronics/Qspice-2) by
J. Marcos Alonso -- file `1.- Digital-PWM/1.- Digital-PWM-C++.qsch` @ `71a5762`.
Adapted and redistributed with the author's permission.

## Files

- `digital_pwm_cblock.qsch` -- Alonso's original QSpice schematic (source of truth).
- `dpwm.cpp` -- Alonso's C-block source; compiles to `dpwm.dll` (the `DPWM` device).
- `digital_pwm_cblock.cir` -- self-contained QUX netlist that references `DPWM`.

## Materialize and simulate

1. `materialize_reference_circuit(recipe_id="digital_pwm_cblock")` -- writes all files.
2. `build_dll_device(source_path="dpwm.cpp")` -- compiles `dpwm.dll` beside the netlist.
3. `run_simulation(source_path="digital_pwm_cblock.cir")` -- runs the netlist.
4. `list_signals` / `measure_waveform` on the produced `.qraw` to inspect the PWM output.

> Note: the `.dll` name must match the C-block device name in the netlist (`DPWM` ->
> `dpwm.dll`), so keep `dpwm.cpp`'s filename. Simulate the bundled `.cir`; the
> behavioral parts are already inlined.
