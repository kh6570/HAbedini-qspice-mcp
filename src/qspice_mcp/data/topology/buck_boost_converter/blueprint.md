# Buck-boost converter (inverting)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin`, `Vout` - input and output DC voltages (the output is inverted, so `Vout` is
  negative); `D` - duty cycle; `fsw` - switching frequency.
- `L`, `C` - energy-transfer inductor and output capacitor; `R_load` - load resistance
  (`|Vout| / Iout`).
- `r_L` - inductor series resistance (DCR); `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The inverting buck-boost charges the inductor directly from the input while the switch
is on, then steers the stored energy into an oppositely-referenced output when the
switch turns off. Volt-second balance gives the CCM ratio `Vout/Vin = -D/(1 - D)`: the
magnitude can be stepped down (`D < 0.5`) or up (`D > 0.5`), and the output polarity is
inverted.

## Power stage

- Switch (`M1`) from `in` to `sw`, driven by `pwm`.
- Energy-transfer inductor `L1` (series resistance `r_L`) from `sw` to `gnd`.
- Rectifier `D1` (or synchronous switch) from `out` to `sw`, oriented for the inverted output.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## DC analysis (CCM)

The ideal magnitude ratio `|Vout|/Vin = D/(1 - D)` assumes a lossless stage. Including
the inductor series resistance gives

```
|Vout| / Vin = D / ((1 - D) + r_L / ((1 - D) * R_load))
```

As with the boost, `r_L` makes the real gain peak and then **roll off** as `D -> 1`
instead of climbing without bound, because the inductor current (and its `r_L` loss)
grows steeply at high duty cycle.

## Sizing (start here)

1. Choose `D = |Vout| / (Vin + |Vout|)`.
2. Average inductor current is `I_L = Iout / (1 - D)`; size `L` from the ripple target
   `L = Vin * D / (dI_L * fsw)`.
3. The capacitor supplies the load during the on-time, so size `C` from
   `dVout = Iout * D / (C * fsw)` and add the ESR term when `r_C` is not negligible.
4. Peak device current is `I_pk = Iout/(1 - D) + dI_L/2`; rate the switch **and** diode
   for `Vin + |Vout|` blocking voltage - higher stress than buck or boost.

## CCM / DCM boundary

The converter leaves continuous conduction at light load:

```
R_lim  = 2 * L * fsw / (1 - D)**2          # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * (1 - D)**2 / (2 * L * fsw) = Vin * D * (1 - D) / (2 * L * fsw)
```

## DCM operation

In discontinuous conduction the inductor current rests at zero for part of each period
and the DC magnitude ratio becomes load-dependent:

```
|Vout| / Vin = D / sqrt(k),   k = 2 * L * fsw / R_load
```

The peak-to-peak output ripple is

```
dVout = L * (D * Vin / (L * fsw) - Vout / R_load)**2 / (2 * Vout * C)
```

## Small-signal model

Alonso's averaged dependent-source method replaces the switch by its average current
source and the diode by its average voltage source, then linearizes about the DC
operating point. In CCM every transfer function shares one second-order denominator
(identical in form to the boost):

```
Den(s) = (R_load + r_C)*L*C*s**2
       + ((1 - D)**2*R_load*r_C*C + L)*s
       + (1 - D)**2*R_load
```

with these results:

- **Control-to-output:** `Gd(s) = Vout*R_load*((1-D)/D)*(1 - (D*L/((1-D)**2*R_load))*s)*(1 + r_C*C*s) / Den(s)`.
  The factor `(1 - (D*L/((1-D)**2*R_load))*s)` is a **right-half-plane zero** at
  `s = (1-D)**2*R_load/(D*L)` - it adds gain while subtracting phase, the defining
  headache of buck-boost control, and the extra `D` makes it bite sooner than the boost.
- **Audio susceptibility:** `Gb(s) = R_load*D*(1-D)*(1 + r_C*C*s) / Den(s)` - same poles as
  `Gd(s)` but no right-half-plane zero.
- **Output impedance:** `Zo(s) = R_load*L*s*(1 + r_C*C*s) / Den(s)` - identical to the
  boost (`k_sl = k_do = D` in both); `Zo(0) = 0`, `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = Den(s) / (D**2*(1 + (R_load + r_C)*C*s))` - the
  characteristic polynomial moves to the numerator; `Zi(0) = (1-D)**2*R_load/D**2`.

In DCM the plant collapses to a **first-order** response and the right-half-plane zero
moves to a very high frequency, so a light-load DCM design can close a faster loop than
the same stage in CCM.

## Control

The plant has a right-half-plane zero that adds phase lag while boosting gain, so the
loop crossover must sit well below `f_rhpz`. Prefer current-mode control to drop the
inductor pole out of the voltage loop; keep voltage-mode bandwidth conservative. Account
for the inverted output polarity in the feedback network and when reading `V(out)`.

## Simulation tips (QSpice)

- **Switched model:** reference feedback to the inverted rail carefully - a sign error
  stalls regulation. Allow a long `.tran` settle window because the loop is
  bandwidth-limited, then verify the output magnitude and polarity with `read_waveform`
  on `V(out)`.
- **Averaged model (fast):** for quick DC and AC studies, replace the switch/diode pair
  with behavioral sources reproducing `<is> = D*<iL>` and `<vD> = D*(<Vin> + <Vout>)`.
  The averaged circuit has no switching edges, so a `.tran` settles almost instantly and
  an `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - the quickest way to
  see the right-half-plane zero before committing to the switched simulation.
