# Boost converter (step-up)

Clean-room CCM design blueprint. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).

## Operating principle

A boost converter stores energy in a series inductor while a low-side switch is on
(inductor across `Vin`), then releases that energy plus the input through the rectifier
into the output when the switch turns off. Volt-second balance gives the CCM ratio
`Vout/Vin = 1/(1 - D)`, so the output is always greater than the input.

## Power stage

- Boost inductor `L1` from `in` to `sw`.
- Low-side switch (`M1`) from `sw` to `gnd`, driven by `pwm`.
- Rectifier `D1` (or synchronous switch) from `sw` to `out`.
- Output capacitor `C1` (with series resistance `R_esr`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## Sizing (start here)

1. Choose `D = 1 - Vin/Vout`.
2. Average inductor (input) current is `I_L = Iout / (1 - D)`; size `L` from the ripple
   target `L = Vin * D / (dI_L * fsw)`.
3. The capacitor supplies the full load during the on-time, so size `C` from
   `dVout = Iout * D / (C * fsw)`.
4. Check the RHP zero `f_rhpz = (1 - D)^2 * R_load / (2*pi*L)` at the worst-case
   (low-input, heavy-load) operating point.

## Control

The plant has a **right-half-plane zero** that adds phase lag while boosting gain, so
the loop crossover must sit well below `f_rhpz`. Prefer current-mode control to drop the
inductor pole out of the voltage loop; keep voltage-mode bandwidth conservative.

## Simulation tips (QSpice)

- Soft-start the duty cycle or pre-charge `C1` to avoid huge inrush at `t = 0`.
- Run `.tran` long enough for the slow (RHP-limited) loop to settle.
- Confirm `V(out) > Vin` and inspect inductor current continuity with `read_waveform`.
