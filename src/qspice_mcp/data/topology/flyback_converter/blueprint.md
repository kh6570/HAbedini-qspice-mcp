# Flyback converter (isolated)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin`, `Vout` - primary input and (isolated) output DC voltages; `D` - duty cycle;
  `fsw` - switching frequency.
- `n = N2/N1` - turns ratio; `L1` - primary magnetizing inductance; `L2 = n**2 * L1` -
  inductance seen from the secondary; `C` - output capacitor; `R_load` - load
  resistance (`Vout / Iout`); `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The flyback is an inverting buck-boost in which the single inductor is split into a
coupled-inductor (transformer) with turns ratio `n`. While the switch is on, energy is
stored in the primary magnetizing inductance `L1`; when the switch turns off, that energy
is delivered through the secondary winding and rectifier into a **galvanically isolated**
output. Volt-second balance gives the CCM ratio `Vout/Vin = n*D/(1 - D)`, so the turns
ratio scales the buck-boost characteristic and sets the input/output isolation.

## Power stage

- Primary winding `L1` (magnetizing inductance) from `in` to `sw`.
- Low-side switch (`M1`) from `sw` to `pri_gnd`, driven by `pwm`.
- Secondary winding (turns ratio `1:n`) referenced to `sec_gnd`.
- Rectifier `D1` from the secondary winding to `out`.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `sec_gnd`.
- Load `R_load` from `out` to `sec_gnd`.

## DC analysis (CCM)

The ideal ratio is `Vout/Vin = n*D/(1 - D)`. The flyback stores and releases its energy
through the magnetizing inductance, so the average currents are

```
I_L2 = Iout                         # secondary magnetizing current = DC output current
I_S  = I_L1 = n*D/(1 - D) * Iout    # average primary (switch) current
I_M1 = n*Iout/(1 - D)               # magnetizing current referred to the primary
```

## Sizing (start here)

1. Choose the turns ratio `n` and duty cycle from `Vout/Vin = n*D/(1 - D)` (a moderate
   `D` near 0.4-0.5 at nominal input keeps switch and diode stress balanced).
2. Size `L1` from the primary ripple target `dI_L1 = D*Vin/(L1*fsw)`; the secondary
   ripple is `dI_L2 = (1 - D)*Vout/(L2*fsw)` with `L2 = n**2 * L1`.
3. The capacitor supplies the load during the on-time, so size `C` from
   `dVout = D*Iout/(fsw*C)` and add the ESR term when `r_C` is not negligible.
4. Rate the switch for `Vin + Vout/n` **plus** the leakage-inductance spike (add a
   snubber/clamp); rate the rectifier for `n*Vin + Vout`. Peak rectifier current is
   `Iout/(1 - D) + dI_L2/2`.

## CCM / DCM boundary

The converter leaves continuous conduction at light load:

```
R_lim  = 2 * n**2 * L1 * fsw / (1 - D)**2     # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * (1 - D)**2 / (2 * n**2 * L1 * fsw)
```

## DCM operation

In discontinuous conduction the magnetizing current rests at zero for part of each period
and the DC ratio becomes load-dependent. A notable result: it is **independent of the
turns ratio** because all the stored energy is delivered every cycle - only the primary
inductance `L1` appears:

```
Vout / Vin = D / sqrt(k),   k = 2 * L1 * fsw / R_load
```

The peak-to-peak output ripple is

```
dVout = n**2 * L1 * (D * Vin / (n * L1 * fsw) - Vout / R_load)**2 / (2 * Vout * C)
```

## Small-signal model

The flyback maps directly onto the buck-boost via the averaged dependent-source method
(switch -> average current source, diode -> average voltage source). **In CCM it is a
buck-boost whose inductance is the secondary-referred value `L2 = n**2 * L1`**, with
input-coupled terms scaled by the turns ratio. Every CCM transfer function shares one
second-order denominator:

```
Den(s) = (R_load + r_C)*n**2*L1*C*s**2
       + ((1 - D)**2*R_load*r_C*C + n**2*L1)*s
       + (1 - D)**2*R_load
```

with these results:

- **Control-to-output:** `Gd(s) = Vout*R_load*((1-D)/D)*(1 - (D*n**2*L1/((1-D)**2*R_load))*s)*(1 + r_C*C*s) / Den(s)`.
  The factor `(1 - (D*n**2*L1/((1-D)**2*R_load))*s)` is a **right-half-plane zero** at
  `s = (1-D)**2*R_load/(D*n**2*L1)` - the defining headache of flyback control.
- **Audio susceptibility:** `Gb(s) = n*R_load*D*(1-D)*(1 + r_C*C*s) / Den(s)` - `n` times
  the buck-boost result, same poles as `Gd(s)`, no right-half-plane zero.
- **Output impedance:** `Zo(s) = R_load*n**2*L1*s*(1 + r_C*C*s) / Den(s)` - `Zo(0) = 0`,
  `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = Den(s) / (n**2*D**2*(1 + (R_load + r_C)*C*s))` - `1/n**2`
  times the buck-boost input impedance; `Zi(0) = (1-D)**2*R_load/(n**2*D**2)`.

In DCM the plant collapses to a **first-order** response and the right-half-plane zero
moves to a very high frequency, so a light-load DCM design can close a faster loop than
the same stage in CCM.

## Control

The plant has a right-half-plane zero that adds phase lag while boosting gain, so the
loop crossover must sit well below `f_rhpz`. Prefer current-mode control. Feedback has to
cross the isolation barrier - typically an optocoupler plus a shunt reference on the
secondary, or primary-side regulation from an auxiliary winding.

## Simulation tips (QSpice)

- **Switched model:** model the coupled inductor with a `K` coupling statement (or two
  coupled inductors with `L2 = n**2 * L1`). Include a leakage inductance and an RCD clamp
  to see the realistic switch turn-off spike; soft-start the duty cycle to limit inrush.
  Run `.tran` long enough for the RHP-limited loop to settle, then check `V(out)` and
  rectifier current continuity with `read_waveform`.
- **Averaged model (fast):** for quick DC and AC studies, replace the switch/diode pair
  with behavioral sources reproducing `<is> = n*D/(1-D)*<iL2>` and `<vD> = D*n*<Vin> +
  D*<Vout>` across an ideal `1:n` transformer. The averaged circuit has no switching
  edges, so a `.tran` settles almost instantly and an `.ac` sweep yields
  `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - the quickest way to see the right-half-plane
  zero before committing to the switched simulation.
