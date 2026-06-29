# Boost converter (step-up)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin`, `Vout` - input and output DC voltages; `D` - duty cycle; `fsw` - switching frequency.
- `L`, `C` - boost inductor and output capacitor; `R_load` - load resistance (`Vout / Iout`).
- `r_L` - inductor series resistance (DCR); `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

A boost converter stores energy in a series inductor while a low-side switch is on
(inductor across `Vin`), then releases that energy plus the input through the rectifier
into the output when the switch turns off. Volt-second balance gives the CCM ratio
`Vout/Vin = 1/(1 - D)`, so the output is always greater than the input.

## Power stage

- Boost inductor `L1` (series resistance `r_L`) from `in` to `sw`.
- Low-side switch (`M1`) from `sw` to `gnd`, driven by `pwm`.
- Rectifier `D1` (or synchronous switch) from `sw` to `out`.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `gnd`.
- Load `R_load` from `out` to `gnd`.

## DC analysis (CCM)

The ideal ratio `Vout/Vin = 1/(1 - D)` assumes a lossless stage. Including the inductor
series resistance gives

```
Vout / Vin = 1 / ((1 - D) + r_L / ((1 - D) * R_load))
```

This is the practically important correction for the boost: instead of rising without
bound as `D -> 1`, the real gain peaks and then **rolls off**, because the growing
inductor current dumps ever more loss into `r_L`. Push the duty cycle too hard and the
output collapses rather than climbing.

## Sizing (start here)

1. Choose `D = 1 - Vin/Vout` (refine with the loss term above near high `D`).
2. Average inductor (input) current is `I_L = Iout / (1 - D)`; size `L` from the ripple
   target `L = Vin * D / (dI_L * fsw)`.
3. The capacitor supplies the full load during the on-time, so size `C` from
   `dVout = Iout * D / (C * fsw)` and add the ESR term when `r_C` is not negligible.
4. Peak device current is `I_pk = Iout/(1 - D) + dI_L/2`; switch/diode blocking voltage is `Vout`.

## CCM / DCM boundary

The converter leaves continuous conduction at light load:

```
R_lim  = 2 * L * fsw / (D * (1 - D)**2)     # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * D * (1 - D)**2 / (2 * L * fsw)
```

## DCM operation

In discontinuous conduction the inductor current rests at zero for part of each period
and the DC ratio becomes load-dependent:

```
Vout / Vin = (1 + sqrt(1 + 4 * D**2 / k)) / 2,   k = 2 * L * fsw / R_load
```

The peak-to-peak output ripple is

```
dVout = L * (D * Vin / (L * fsw) - Vout / R_load)**2 / (2 * (Vout - Vin) * C)
```

A DCM design needs the output capacitor pre-charged or an initial-condition assist in
simulation, since the DC equation has a second (non-physical) root that the solver can
otherwise settle on.

## Small-signal model

Alonso's averaged dependent-source method replaces the switch by its average current
source and the diode by its average voltage source, then linearizes about the DC
operating point. In CCM every transfer function shares one second-order denominator:

```
Den(s) = (R_load + r_C)*L*C*s**2
       + ((1 - D)**2*R_load*r_C*C + L)*s
       + (1 - D)**2*R_load
```

with these results:

- **Control-to-output:** `Gd(s) = Vout*R_load*(1-D)*(1 - (L/((1-D)**2*R_load))*s)*(1 + r_C*C*s) / Den(s)`.
  The factor `(1 - (L/((1-D)**2*R_load))*s)` is a **right-half-plane zero** at
  `s = (1-D)**2*R_load/L` - it adds gain while subtracting phase, the defining headache
  of boost control.
- **Audio susceptibility:** `Gb(s) = R_load*(1-D)*(1 + r_C*C*s) / Den(s)` - same poles as
  `Gd(s)` but no right-half-plane zero.
- **Output impedance:** `Zo(s) = R_load*L*s*(1 + r_C*C*s) / Den(s)` - `Zo(0) = 0`,
  `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = Den(s) / (1 + (R_load + r_C)*C*s)` - the characteristic
  polynomial moves to the numerator; `Zi(0) = (1-D)**2*R_load`.

In DCM the plant collapses to a **first-order** response and the right-half-plane zero
moves to a very high frequency, so a light-load DCM design can close a faster loop than
the same stage in CCM.

## Control

The plant has a right-half-plane zero that adds phase lag while boosting gain, so the
loop crossover must sit well below `f_rhpz`. Prefer current-mode control to drop the
inductor pole out of the voltage loop; keep voltage-mode bandwidth conservative.

## Simulation tips (QSpice)

- **Switched model:** soft-start the duty cycle or pre-charge `C1` to avoid huge inrush
  at `t = 0`. Run `.tran` long enough for the slow (RHP-limited) loop to settle, then
  confirm `V(out) > Vin` and inspect inductor current continuity with `read_waveform`.
- **Averaged model (fast):** for quick DC and AC studies, replace the switch/diode pair
  with behavioral sources reproducing `<is> = D*<iL>` and `<vD> = D*<Vout>`. The averaged
  circuit has no switching edges, so a `.tran` settles almost instantly and an `.ac`
  sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - the quickest way to see the
  right-half-plane zero before committing to the switched simulation.
