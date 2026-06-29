# Forward converter (isolated)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin`, `Vout` - primary input and (isolated) output DC voltages; `D` - duty cycle;
  `fsw` - switching frequency.
- `n = N2/N1` - power transformer turns ratio; `n31 = N3/N1` - reset (tertiary) winding
  turns ratio; `LM` - primary magnetizing inductance.
- `L`, `C` - secondary output filter inductor and capacitor; `R_load` - load resistance
  (`Vout / Iout`); `r_L` - output inductor DCR; `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The forward converter is a **buck stage placed behind an isolation transformer**. While
the switch is on, the transformer transfers power directly to the secondary, the rectifier
`D1` conducts, and the output inductor `L` charges from `n*Vin`. When the switch turns
off, the freewheel diode `D2` carries the inductor current and the transformer is reset
through a tertiary winding (`N3`) and reset diode `D3`. Because the output stage is an LC
filter with continuous current, volt-second balance gives the buck-like ratio
`Vout/Vin = n*D`, with **galvanic isolation** and **no right-half-plane zero**.

## Power stage

- Power transformer primary `N1` from `in` to `sw`; secondary `N2` (ratio `1:n`) referenced
  to `sec_gnd`; reset/tertiary winding `N3` returned to `pri_gnd`.
- Low-side switch (`M1`) from `sw` to `pri_gnd`, driven by `pwm`.
- Forward rectifier `D1` from the secondary to the output inductor; freewheel diode `D2`
  across the inductor input; reset diode `D3` on the tertiary winding.
- Output inductor `L` (series resistance `r_L`) into the output node.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `sec_gnd`; load `R_load`.

## DC analysis (CCM)

The ideal ratio is `Vout/Vin = n*D`. Including the output inductor series resistance:

```
Vout / Vin = n*D / (1 + r_L / R_load)
```

The capacitor ESR does not change the DC ratio (no DC current flows in `C`).

## Transformer reset (the defining constraint)

The magnetizing flux must return to zero every cycle or it will "staircase" into
saturation. With a tertiary reset winding (`n31 = N3/N1`) the demagnetization interval is
`dt_reset = n31*D*T`, and it must finish before the period ends:

```
dt_reset = n31*D/fsw < (1 - D)/fsw   =>   D_max < 1 / (1 + n31)
```

So an equal-turns reset winding (`n31 = 1`) limits the duty cycle to `D < 0.5`. The
reset method also fixes the switch voltage stress at `(1 + 1/n31)*Vin` and the reset-diode
stress at `(1 + n31)*Vin`. RCD clamps and active-clamp resets trade this differently.

## Sizing (start here)

1. Pick the turns ratio `n` and a duty cycle with reset margin (e.g. `D <= 0.45` for
   `n31 = 1`); then `Vout = n*D*Vin`.
2. Size `L` from the ripple target `dI_L = (n*Vin - Vout)*D/(L*fsw)` (the buck rule with
   reflected input `n*Vin`).
3. Size `C` from `dVout = dI_L/(8*C*fsw)`; add the ESR term `r_C*dI_L` when needed.
4. Rate the switch for `(1 + 1/n31)*Vin` plus the leakage spike; rate the rectifiers for
   the reflected voltages; peak rectifier/inductor current is `Iout + dI_L/2`.

## CCM / DCM boundary

```
R_lim  = 2 * L * fsw / (1 - D)            # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * (1 - D) / (2 * L * fsw)
```

## DCM operation

In discontinuous conduction the output-inductor current rests at zero and the ratio
becomes load-dependent - the buck DCM result scaled by `n`:

```
Vout / Vin = 2*n / (1 + sqrt(1 + 4*k/D**2)),   k = 2 * L * fsw / R_load
```

with peak-to-peak ripple

```
dVout = L * ((n*Vin - Vout)*D/(L*fsw) - Vout/R_load)**2 / (2 * C * (1 - Vout/(n*Vin)) * Vout)
```

## Small-signal model

The forward maps directly onto the buck via the averaged dependent-source method (switch
-> average current source, diodes -> average voltage sources). **Every CCM transfer
function is the buck result scaled by the turns ratio**, sharing one second-order
denominator:

```
Den(s) = L*C*(1 + r_C/R_load)*s**2
       + (L/R_load + r_C*C + r_L*C + r_L*r_C*C/R_load)*s
       + (1 + r_L/R_load)
```

with these results:

- **Control-to-output:** `Gd(s) = n*Vin*(1 + r_C*C*s) / Den(s)` (= `(Vout/D)*(1 + r_C*C*s)/Den(s)`)
  - `n` times the buck, a single ESR zero at `1/(r_C*C)`, **no right-half-plane zero**.
- **Audio susceptibility:** `Gb(s) = n*D*(1 + r_C*C*s) / Den(s)` - `n` times the buck,
  same dynamics as `Gd(s)`.
- **Output impedance:** `Zo(s) = (r_L + L*s)*(1 + r_C*C*s) / Den(s)` - identical to the
  buck, independent of `n`; `Zo(0) ~ r_L`, `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = (R_load/(n**2*D**2))*Den(s) / (1 + (R_load + r_C)*C*s)` -
  the buck input impedance divided by `n**2`; `Zi(0) = (R_load + r_L)/(n**2*D**2)`.

In DCM the plant collapses to a **first-order** response and the DC gain becomes
load-dependent (still `n` times the buck).

## Control

Because there is no right-half-plane zero, the forward is one of the easier isolated
plants to compensate - a Type-II/Type-III voltage-mode loop or current-mode control both
work, crossing over well below `fsw/5`. Feedback crosses the isolation barrier via an
optocoupler plus shunt reference, or primary-side regulation.

## Simulation tips (QSpice)

- **Switched model:** model the transformer with coupled inductors (primary, secondary,
  reset). Include the magnetizing inductance `LM` and the reset path so you can confirm
  the flux resets within `(1 - D)*T`; watch the switch voltage reach `(1 + 1/n31)*Vin` and
  add a leakage snubber. Run `.tran` past the LC settling and check `V(out) ~ n*D*Vin`
  with `read_waveform`.
- **Averaged model (fast):** for quick DC and AC studies, drive an ideal `1:n` transformer
  with behavioral sources reproducing `<is> = n*D*<iL>` and `<vD2> = n*D*<Vin>`, feeding the
  `L`-`r_L`-`C`-`r_C`-`R_load` filter. With no switching edges a `.tran` settles almost
  instantly and an `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - confirming
  the clean second-order (no RHP zero) response before the switched run.
