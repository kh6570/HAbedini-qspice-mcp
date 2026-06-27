# Buck-boost converter (inverting)

Clean-room CCM design blueprint. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).

## Operating principle

The inverting buck-boost charges the inductor directly from the input while the switch
is on, then steers the stored energy into an oppositely-referenced output when the
switch turns off. Volt-second balance gives `Vout/Vin = -D/(1 - D)`: the magnitude can
be stepped down (`D < 0.5`) or up (`D > 0.5`), and the output polarity is inverted.

## Power stage

- Switch (`M1`) from `in` to `sw`, driven by `pwm`.
- Energy-transfer inductor `L1` from `sw` to `gnd`.
- Rectifier `D1` from `out` to `sw` (oriented for the inverted output).
- Output capacitor `C1` (with series resistance `R_esr`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## Sizing (start here)

1. Choose `D = |Vout| / (Vin + |Vout|)`.
2. Average inductor current is `I_L = Iout / (1 - D)`; size `L` from the ripple target
   `L = Vin * D / (dI_L * fsw)`.
3. The capacitor supplies the load during the on-time, so size `C` from
   `dVout = Iout * D / (C * fsw)`.
4. Rate the switch and diode for `Vin + |Vout|` blocking voltage.

## Control

A **right-half-plane zero** (frequency falls with load and rises with `D`) limits the
achievable bandwidth, as in the boost. Current-mode control is standard. Account for the
inverted output polarity in the feedback network and when reading `V(out)`.

## Simulation tips (QSpice)

- Reference feedback to the inverted rail carefully; a sign error stalls regulation.
- Allow a long `.tran` settle window because the loop is bandwidth-limited.
- Verify the output magnitude and polarity with `read_waveform` on `V(out)`.
