# Buck converter (step-down)

Clean-room CCM design blueprint. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).

## Operating principle

A buck converter chops the input rail with a high-side switch and filters the result
with an `L`/`C` low-pass network. During the on-time the inductor charges from
`Vin - Vout`; during the off-time it freewheels through the diode (or synchronous
low-side switch) discharging into the load. In continuous conduction mode (CCM) the
volt-second balance on the inductor fixes the DC conversion ratio at `Vout/Vin = D`.

## Power stage

- High-side switch (`M1`) between `in` and `sw`, driven by `pwm`.
- Freewheeling diode `D1` (or synchronous switch) from `gnd` to `sw`.
- Filter inductor `L1` from `sw` to `out`.
- Output capacitor `C1` (with series resistance `R_esr`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## Sizing (start here)

1. Choose `D = Vout / Vin`.
2. Pick `fsw`, then set the inductor ripple target (typically 20-40 % of `Iout`) and
   solve `L = (Vin - Vout) * D / (dI_L * fsw)`.
3. Size `C` from the output-ripple budget `dVout = dI_L / (8 * C * fsw)`.
4. Verify CCM at minimum load against `L_crit = (1 - D) * R_load / (2 * fsw)`.

## Control

The control-to-output plant is a second-order LC low-pass (resonance at
`1 / (2*pi*sqrt(L*C))`) with an ESR zero and **no right-half-plane zero**. Voltage-mode
control closes cleanly with a Type-III compensator; current-mode control collapses the
plant to first order. Cross over well below `fsw/5`.

## Simulation tips (QSpice)

- Author the power stage with `add_component`/`add_wire`; drive `pwm` from a C-block or
  behavioral PWM source.
- Use `.tran` with `uic` and let the output settle several `L*C` time constants.
- Assert the regulated rail with `read_waveform`/`measure_step_response` on `V(out)`.
