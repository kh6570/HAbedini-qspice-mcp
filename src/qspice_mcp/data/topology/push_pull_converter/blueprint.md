# Push-pull converter (isolated)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin` (bus `VB`), `Vout` - primary input and (isolated) output DC voltages; `D` - per-switch
  duty cycle (on-time within its half-period); `fsw` - per-switch switching frequency.
- `n = N2/N1` - power transformer turns ratio, where `N1` is one half of the center-tapped primary.
- `L`, `C` - secondary output filter inductor and capacitor; `R_load` - load resistance
  (`Vout / Iout`); `r_L` - output inductor DCR; `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The push-pull is a **buck stage behind a center-tapped transformer driven by two switches**. The
input bus feeds the primary center tap; `S1` and `S2` alternately pull the two ends of the
primary (`N1a`, `N1b`) to ground, so each half-cycle the full bus `Vin` sits across one
half-winding with opposite polarity. A full-wave secondary rectifier (`D1`-`D4`) delivers energy
into the output inductor `L`, which charges from `n*Vin`. Because the output stage is an LC
filter with continuous current, volt-second balance gives the buck-like ratio `Vout/Vin = n*D`,
with **galvanic isolation** and **no right-half-plane zero**. The alternating drive self-resets
the core (no reset winding, no `D < 0.5` limit). The catch: when one switch conducts, the coupled
half-winding reflects `Vin` onto the other end, so the **off switch must block `2*Vin`**.

## Power stage

- Center-tapped primary: center tap at `in`; `N1a` from `in` to `sw1`, `N1b` from `in` to `sw2`.
- Two low-side switches `S1` (`sw1` -> `pri_gnd`) and `S2` (`sw2` -> `pri_gnd`), driven by
  complementary `pwm` with dead-time. Both are ground-referenced (no high-side drivers).
- Secondary `N2` (ratio `1:n` per half-winding) feeding a full-wave rectifier `D1`-`D4`
  referenced to `sec_gnd`.
- Output inductor `L` (series resistance `r_L`) into the output node.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `sec_gnd`; load `R_load`.

## DC analysis (CCM)

The ideal ratio is `Vout/Vin = n*D`. Including the output inductor series resistance:

```
Vout / Vin = n*D / (1 + r_L / R_load)
```

The capacitor ESR does not change the DC ratio (no DC current flows in `C`). The ratio equals
the full-bridge because the full bus reaches one half-winding each cycle.

## Sizing (start here)

1. Pick the turns ratio `n` (per half-winding) and a duty cycle `D`; then `Vout = n*D*Vin`.
2. Size `L` from the ripple target `dI_L = (n*Vin - Vout)*D/(L*fsw)` (the buck rule with
   reflected primary voltage `n*Vin`).
3. Size `C` from `dVout = dI_L/(16*C*fsw)` (note the `1/16`, not `1/8`: the output is refreshed
   twice per period); add the ESR term `r_C*dI_L` when needed.
4. **Rate each switch for `2*Vin`** plus the leakage spike (the defining push-pull constraint);
   peak switch current is `n*(Iout + dI_L/2)`. Rate each rectifier for `n*Vin`; peak
   rectifier/inductor current is `Iout + dI_L/2`.

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

The push-pull is **dynamically identical to the full-bridge** (and to the forward in form): the
averaged dependent-source method (switches -> average current sources, rectifier diodes ->
average voltage sources) yields one shared second-order denominator:

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
  buck input impedance divided by `n**2*D**2`; `Zi(0) = (R_load + r_L)/(n**2*D**2)`.

In DCM the plant collapses to a **first-order** response and the DC gain becomes load-dependent.

## Control

Because there is no right-half-plane zero, the push-pull compensates like a buck - a
Type-II/Type-III voltage-mode loop or current-mode control both work, crossing over well below
`fsw/5`. The push-pull is **especially prone to flux imbalance / staircase saturation**: any
mismatch between the two switch on-times or half-winding resistances walks the DC flux toward
one rail, so **peak-current-mode control** (which balances volt-seconds cycle-by-cycle) is
strongly preferred over pure voltage mode. Keep the two half-windings tightly coupled and add a
leakage snubber. Feedback crosses the isolation barrier via an optocoupler plus shunt reference,
or primary-side regulation.

## Push-pull vs. full-bridge

Identical ratio (`n*D`), ripple, boundary, and small-signal dynamics. The trade is device count
vs. voltage stress:

- **Push-pull:** only two ground-referenced switches -> simplest gate drive, but each switch
  blocks `2*Vin`. Best at **low input voltage**.
- **Full-bridge:** four switches (needs high-side drivers), but each blocks only `Vin`. Best at
  **high input voltage / high power**.

## Simulation tips (QSpice)

- **Switched model:** model the center-tapped primary as two tightly-coupled windings and `S1`/`S2`
  as ground-referenced switches with dead-time. Confirm each half-winding sees `+/- Vin`, that the
  off switch reaches `2*Vin`, and add a leakage snubber. Run `.tran` past the LC settling and
  check `V(out) ~ n*D*Vin` with `read_waveform`; verify the output ripple sits at `2*fsw` and
  watch the magnetizing current for staircase drift.
- **Averaged model (fast):** for quick DC and AC studies, drive an ideal `1:n` transformer with
  behavioral sources reproducing `<is> = n*D*<iL>` and `<vD> = n*D*<Vin>`, feeding the
  `L`-`r_L`-`C`-`r_C`-`R_load` filter. With no switching edges a `.tran` settles almost instantly
  and an `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - confirming the clean
  second-order (no RHP zero) response before the switched run.
