# Buck converter (step-down)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin`, `Vout` - input and output DC voltages; `D` - duty cycle; `fsw` - switching frequency.
- `L`, `C` - filter inductor and output capacitor; `R_load` - load resistance (`Vout / Iout`).
- `r_L` - inductor series resistance (DCR); `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

A buck converter chops the input rail with a high-side switch and filters the result
with an `L`/`C` low-pass network. During the on-time (`D*T`) the inductor charges from
`Vin - Vout`; during the off-time it freewheels through the diode (or synchronous
low-side switch) discharging into the load. In continuous conduction mode (CCM) the
volt-second balance on the inductor fixes the ideal DC conversion ratio at `Vout/Vin = D`.

## Power stage

- High-side switch (`M1`) between `in` and `sw`, driven by `pwm`.
- Freewheeling diode `D1` (or synchronous switch) from `gnd` to `sw`.
- Filter inductor `L1` (series resistance `r_L`) from `sw` to `out`.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## DC analysis (CCM)

The ideal ratio `Vout/Vin = D` assumes a lossless stage. Including the inductor
series resistance gives the more accurate result

```
Vout / Vin = D / (1 + r_L / R_load)
```

The capacitor ESR does **not** change the DC ratio because no DC current flows through
`C`; it does add conduction loss in AC operation. The inductor DCR `r_L`, by contrast,
carries the full load current and therefore dominates the DC error.

## Sizing (start here)

1. Choose `D = Vout / Vin` (refine with the loss term above if `r_L` is significant).
2. Pick `fsw`, then set the inductor ripple target (typically 20-40 % of `Iout`) and
   solve `L = (Vin - Vout) * D / (dI_L * fsw)`.
3. Size `C` from the output-ripple budget `dVout = dI_L / (8 * C * fsw)` and add the ESR
   term `r_C * dI_L` when the capacitor ESR is not negligible.
4. Verify CCM at minimum load against `L_crit = (1 - D) * R_load / (2 * fsw)`.
5. Peak device current is `I_pk = Iout + dI_L / 2`; switch/diode blocking voltage is `Vin`.

## CCM / DCM boundary

The converter leaves continuous conduction when the load is light enough that the
inductor current reaches zero each cycle. The boundary is

```
R_lim  = 2 * L * fsw / (1 - D)        # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * (1 - D) / (2 * L * fsw)
```

## DCM operation

In discontinuous conduction the inductor current rests at zero for part of each period
and the stage behaves like a current source feeding the load. The DC ratio becomes
load-dependent:

```
Vout / Vin = 2 / (1 + sqrt(1 + 4 * k / D**2)),   k = 2 * L * fsw / R_load
```

Note that `r_L` drops out of the DCM ratio (the current-source behaviour makes the
series resistance far less relevant than in CCM). The peak-to-peak output ripple is

```
dVout = L / (2 * C * (1 - Vout/Vin) * Vout) * ((Vin - Vout) * D / (L * fsw) - Vout / R_load)**2
```

## Small-signal model

Alonso's averaged dependent-source method replaces the switch by its average current
source and the diode by its average voltage source, then linearizes about the DC
operating point. In CCM every transfer function shares one second-order denominator
(the characteristic polynomial):

```
Den(s) = L*C*(1 + r_C/R_load)*s**2
       + (L/R_load + r_C*C + r_L*C + r_L*r_C*C/R_load)*s
       + (1 + r_L/R_load)
```

with these results:

- **Control-to-output:** `Gd(s) = Vin * (1 + r_C*C*s) / Den(s)` - second-order low-pass,
  one ESR zero at `1/(r_C*C)`, and **no right-half-plane zero** (unlike the boost and
  buck-boost stages).
- **Audio susceptibility:** `Gb(s) = D * (1 + r_C*C*s) / Den(s)` - same dynamics as
  `Gd(s)`, only the DC gain differs.
- **Output impedance:** `Zo(s) = (r_L + L*s)(1 + r_C*C*s) / Den(s)` - parallel of the
  inductor, capacitor, and load branches; `Zo(0) ~ r_L`, `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = (R_load/D**2) * Den(s) / (1 + (R_load + r_C)*C*s)` -
  the characteristic polynomial moves to the numerator; `Zi(0) = (R_load + r_L)/D**2`.

In DCM the plant collapses to a **first-order** response, which is much easier to
compensate than the CCM resonant pole pair.

## Control

The CCM control-to-output plant is a second-order LC low-pass (resonance near
`1 / (2*pi*sqrt(L*C))`) with an ESR zero and no right-half-plane zero. Voltage-mode
control closes cleanly with a Type-III compensator; current-mode control collapses the
plant to first order. Cross over well below `fsw/5`.

## Simulation tips (QSpice)

- **Switched model:** author the power stage with `add_component`/`add_wire`; drive
  `pwm` from a C-block or behavioral PWM source. Use `.tran` with `uic` and let the
  output settle several `L*C` time constants, then assert the regulated rail with
  `read_waveform`/`measure_step_response` on `V(out)`.
- **Averaged model (fast):** for quick DC and AC studies, replace the switch/diode pair
  with behavioral sources that reproduce `<is> = D*<iL>` and `<vD> = D*<Vin>`. This
  averaged circuit has no switching edges, so a `.tran` settles almost instantly and an
  `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - ideal for compensator
  design before committing to the switched simulation.
