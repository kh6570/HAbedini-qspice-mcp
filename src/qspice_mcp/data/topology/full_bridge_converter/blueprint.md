# Full-bridge converter (isolated)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin` (bus `VB`), `Vout` - primary input and (isolated) output DC voltages; `D` - per-pair
  duty cycle (on-time within its half-period); `fsw` - per-pair switching frequency.
- `n = N2/N1` - power transformer turns ratio.
- `L`, `C` - secondary output filter inductor and capacitor; `R_load` - load resistance
  (`Vout / Iout`); `r_L` - output inductor DCR; `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The full-bridge is a **buck stage placed behind an isolation transformer that is driven from
both directions by an H-bridge**. Four switches form two legs across the input bus. Diagonal
pairs conduct alternately: `S1+S2` apply `+Vin` across the primary for the on-time, then `S3+S4`
apply `-Vin`. Each half-cycle a full-wave secondary rectifier (`D1`-`D4`) delivers energy into
the output inductor `L`, which charges from `n*Vin`. Because the output stage is an LC filter
with continuous current, volt-second balance gives the buck-like ratio `Vout/Vin = n*D`, with
**galvanic isolation** and **no right-half-plane zero**. Driving the core symmetrically means it
self-resets each period - no reset winding and no `D < 0.5` limit - and each switch blocks only
the full bus `Vin`.

## Power stage

- H-bridge: leg A = `S1` (in -> `sw_a`) + `S4` (`sw_a` -> `pri_gnd`); leg B = `S3` (in -> `sw_b`)
  + `S2` (`sw_b` -> `pri_gnd`), all driven by `pwm` with dead-time. Anti-parallel diodes carry
  the transformer magnetizing current during the idle (dead-time) intervals.
- Power transformer primary `N1` from `sw_a` to `sw_b`; secondary `N2` (ratio `1:n`) feeding a
  full-wave rectifier `D1`-`D4` referenced to `sec_gnd`.
- Output inductor `L` (series resistance `r_L`) into the output node.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `sec_gnd`; load `R_load`.

## DC analysis (CCM)

The ideal ratio is `Vout/Vin = n*D`. Including the output inductor series resistance:

```
Vout / Vin = n*D / (1 + r_L / R_load)
```

The capacitor ESR does not change the DC ratio (no DC current flows in `C`). Because the full
bus reaches the primary (no divider), the ratio is twice the half-bridge's `n*D/2`.

## Sizing (start here)

1. Pick the turns ratio `n` and a duty cycle `D`; then `Vout = n*D*Vin`. Unlike the forward
   there is no reset-imposed duty ceiling.
2. Size `L` from the ripple target `dI_L = (n*Vin - Vout)*D/(L*fsw)` (the buck rule with
   reflected primary voltage `n*Vin`).
3. Size `C` from `dVout = dI_L/(16*C*fsw)` (note the `1/16`, not `1/8`: the output is refreshed
   twice per period); add the ESR term `r_C*dI_L` when needed.
4. Rate each of the four switches for the full bus `Vin` plus the leakage spike; peak switch
   current is `n*(Iout + dI_L/2)`. Rate each rectifier for `n*Vin`; peak rectifier/inductor
   current is `Iout + dI_L/2`.

## CCM / DCM boundary

```
R_lim  = 4 * L * fsw / (1 - D)            # CCM when R_load < R_lim, DCM when R_load > R_lim
Io_lim = Vout * (1 - D) / (4 * L * fsw)
```

The factor `4` (vs. `2` for the buck/forward) reflects the doubled effective output-ripple
frequency `2*fsw`.

## DCM operation

In discontinuous conduction the output-inductor current rests at zero and the ratio becomes
load-dependent:

```
Vout / Vin = 2*n / (1 + sqrt(1 + 4*k/D**2)),   k = 4 * L * fsw / R_load
```

with peak inductor (and reflected switch) current

```
i_pk = D * (n*Vin - Vout) / (2 * L * fsw)
```

## Small-signal model

The full-bridge maps directly onto the buck via the averaged dependent-source method (switches
-> average current sources, rectifier diodes -> average voltage sources), giving a CCM model
**identical in form to the forward converter**. Every CCM transfer function shares one
second-order denominator:

```
Den(s) = L*C*(1 + r_C/R_load)*s**2
       + (L/R_load + r_C*C + r_L*C + r_L*r_C*C/R_load)*s
       + (1 + r_L/R_load)
```

with these results:

- **Control-to-output:** `Gd(s) = n*Vin*(1 + r_C*C*s) / Den(s)`
  (= `(Vout/D)*(1 + r_L/R_load)*(1 + r_C*C*s)/Den(s)`) - `n` times the buck, a single ESR zero
  at `1/(r_C*C)`, **no right-half-plane zero**.
- **Audio susceptibility:** `Gb(s) = n*D*(1 + r_C*C*s) / Den(s)` - `n` times the buck, same
  dynamics as `Gd(s)`.
- **Output impedance:** `Zo(s) = (r_L + L*s)*(1 + r_C*C*s) / Den(s)` - identical to the buck,
  independent of `n`; `Zo(0) ~ r_L`, `Zo(inf) ~ r_C`.
- **Input impedance:** `Zi(s) = (R_load/(n**2*D**2))*Den(s) / (1 + (R_load + r_C)*C*s)` - the
  buck input impedance divided by `n**2*D**2`; `Zi(0) = (R_load + r_L)/(n**2*D**2)`. Unlike the
  half-bridge there is no input-capacitor divider to parallel.

In DCM the plant collapses to a **first-order** response and the DC gain becomes load-dependent.

## Control

Because there is no right-half-plane zero, the full-bridge is one of the easier isolated plants
to compensate - a Type-II/Type-III voltage-mode loop or current-mode control both work, crossing
over well below `fsw/5`. Watch for **flux imbalance**: asymmetric on-times between the diagonal
pairs push a DC magnetizing current toward saturation; a DC-blocking capacitor in series with
the primary or peak-current-mode control mitigates it. Honor the diagonal-pair dead-time to
avoid shoot-through. Feedback crosses the isolation barrier via an optocoupler plus shunt
reference, or primary-side regulation.

## Full-bridge vs. half-bridge vs. push-pull

- **vs. half-bridge:** the full bridge applies `Vin` (not `Vin/2`) to the primary, so the ratio
  is `n*D` (twice the half-bridge) and `Zi` has no input-capacitor divider - at the cost of two
  extra switches.
- **vs. push-pull:** identical dynamics and ratio, but the full-bridge switches block only `Vin`
  (the push-pull's block `2*Vin`), favoring higher input voltages; the push-pull needs only two
  ground-referenced switches (simpler drive).

## Simulation tips (QSpice)

- **Switched model:** model the transformer with coupled inductors and the four switches as two
  diagonal pairs with dead-time. Confirm the primary swings `+/- Vin`, that each switch off-voltage
  reaches `Vin`, and add a leakage snubber. Run `.tran` past the LC settling and check
  `V(out) ~ n*D*Vin` with `read_waveform`; verify the output ripple sits at `2*fsw`.
- **Averaged model (fast):** for quick DC and AC studies, drive an ideal `1:n` transformer with
  behavioral sources reproducing `<is> = n*D*<iL>` and `<vD> = n*D*<Vin>`, feeding the
  `L`-`r_L`-`C`-`r_C`-`R_load` filter. With no switching edges a `.tran` settles almost instantly
  and an `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - confirming the clean
  second-order (no RHP zero) response before the switched run.
