# Half-bridge converter (isolated)

Clean-room design blueprint covering continuous (CCM) and discontinuous (DCM)
conduction plus the small-signal model. Theory cited to J. Marcos Alonso,
*Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743).
Every equation below is a repo-owned restatement of standard converter theory;
no schematic, netlist, or source file from the referenced repository is copied.

## Symbol legend

- `Vin` (bus `VB`), `Vout` - primary input and (isolated) output DC voltages; `D` - per-switch
  duty cycle (on-time within its half-period); `fsw` - per-switch switching frequency.
- `n = N2/N1` - power transformer turns ratio.
- `C_B` - each of the two series input divider capacitors (`CB1 = CB2 = C_B`); `r_B` - their ESR.
- `L`, `C` - secondary output filter inductor and capacitor; `R_load` - load resistance
  (`Vout / Iout`); `r_L` - output inductor DCR; `r_C` - output capacitor ESR.
- `s` - Laplace variable; angle-bracket "averaged" quantities are taken over one switching period.

## Operating principle

The half-bridge is a **buck stage placed behind an isolation transformer that is driven from
both directions**. Two switches `S1` (high side) and `S2` (low side) form a totem-pole across
the input bus; two series capacitors `CB1`/`CB2` split the bus so their midpoint sits at
`Vin/2`. The transformer primary connects between the switch midpoint and the capacitor
midpoint, so it swings `+Vin/2` when `S1` conducts and `-Vin/2` when `S2` conducts. Each
half-cycle a full-wave secondary rectifier (`D1`-`D4`) delivers energy into the output inductor
`L`, which charges from `n*Vin/2`. Because the output stage is an LC filter with continuous
current, volt-second balance gives the buck-like ratio `Vout/Vin = n*D/2`, with **galvanic
isolation** and **no right-half-plane zero**. Driving the core symmetrically means it
self-resets each period - there is no reset winding and no `D < 0.5` limit.

## Power stage

- Switch totem-pole `S1` (from `in` to `sw_mid`) and `S2` (from `sw_mid` to `pri_gnd`), driven
  by complementary `pwm` with dead-time.
- Input divider capacitors `CB1`/`CB2` in series across the bus; their midpoint `cap_mid` at
  `Vin/2`. Anti-parallel diodes across the switches carry the transformer magnetizing current
  during the idle (dead-time) intervals.
- Power transformer primary `N1` from `sw_mid` to `cap_mid`; secondary `N2` (ratio `1:n`)
  feeding a full-wave rectifier `D1`-`D4` referenced to `sec_gnd`.
- Output inductor `L` (series resistance `r_L`) into the output node.
- Output capacitor `C1` (series resistance `r_C`) from `out` to `sec_gnd`; load `R_load`.

## DC analysis (CCM)

The ideal ratio is `Vout/Vin = n*D/2`. Including the output inductor series resistance:

```
Vout / Vin = (n*D/2) / (1 + r_L / R_load)
```

The capacitor ESR does not change the DC ratio (no DC current flows in `C`). The `1/2` is the
input-divider factor: the primary only ever sees `Vin/2`.

## Sizing (start here)

1. Pick the turns ratio `n` and a duty cycle `D`; then `Vout = (n*D/2)*Vin`. Unlike the
   forward there is no reset-imposed duty ceiling.
2. Size `L` from the ripple target `dI_L = (n*Vin/2 - Vout)*D/(L*fsw)` (the buck rule with
   reflected primary voltage `n*Vin/2`).
3. Size `C` from `dVout = dI_L/(16*C*fsw)` (note the `1/16`, not `1/8`: the output is refreshed
   twice per period); add the ESR term `r_C*dI_L` when needed.
4. Rate each switch for the full bus `Vin` plus the leakage spike; peak switch current is
   `n*(Iout + dI_L/2)`. Rate each rectifier for `n*Vin/2`; peak rectifier/inductor current is
   `Iout + dI_L/2`.

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
Vout / Vin = n / (1 + sqrt(1 + 4*k/D**2)),   k = 4 * L * fsw / R_load
```

with peak inductor (and reflected switch) current

```
i_pk = D * (n*Vin - 2*Vout) / (4 * L * fsw)
```

## Small-signal model

The half-bridge maps directly onto the buck via the averaged dependent-source method (switches
-> average current sources, rectifier diodes -> average voltage sources). **Every CCM transfer
function is the buck result scaled through the transformer**, sharing one second-order
denominator:

```
Den(s) = L*C*(1 + r_C/R_load)*s**2
       + (L/R_load + r_C*C + r_L*C + r_L*r_C*C/R_load)*s
       + (1 + r_L/R_load)
```

with these results:

- **Control-to-output:** `Gd(s) = (n*Vin/2)*(1 + r_C*C*s) / Den(s)`
  (= `(Vout/D)*(1 + r_L/R_load)*(1 + r_C*C*s)/Den(s)`) - `n/2` times the buck, a single ESR
  zero at `1/(r_C*C)`, **no right-half-plane zero**.
- **Audio susceptibility:** `Gb(s) = (n*D/2)*(1 + r_C*C*s) / Den(s)` - `n/2` times the buck,
  same dynamics as `Gd(s)`.
- **Output impedance:** `Zo(s) = (r_L + L*s)*(1 + r_C*C*s) / Den(s)` - identical to the buck,
  independent of `n`; `Zo(0) ~ r_L`, `Zo(inf) ~ r_C`.
- **Input impedance:** the active converter input `Z_C(s) = (R_load/(n**2*D**2))*Den(s) /
  (1 + (R_load + r_C)*C*s)` in parallel with the passive input divider
  `Z_B(s) = 2*r_B + 2/(C_B*s)`, i.e. `Zi(s) = Z_B*Z_C/(Z_B + Z_C)`; `Z_C(0) = (R_load + r_L)/(n**2*D**2)`.

In DCM the plant collapses to a **first-order** response and the DC gain becomes load-dependent.

## Control

Because there is no right-half-plane zero, the half-bridge is one of the easier isolated plants
to compensate - a Type-II/Type-III voltage-mode loop or current-mode control both work, crossing
over well below `fsw/5`. Current-mode control also helps balance the transformer flux. Watch for
**flux imbalance**: asymmetric on-times between `S1` and `S2` push a DC magnetizing current that
can walk the core toward saturation; a DC-blocking capacitor in series with the primary or
peak-current-mode control mitigates it. Feedback crosses the isolation barrier via an
optocoupler plus shunt reference, or primary-side regulation.

## Simulation tips (QSpice)

- **Switched model:** model the transformer with coupled inductors, the two switches with
  complementary gate drives and dead-time, and the input divider `CB1`/`CB2`. Confirm the
  primary swings `+/- Vin/2`, that the switch off-voltage reaches `Vin`, and add a leakage
  snubber. Run `.tran` past the LC settling and check `V(out) ~ (n*D/2)*Vin` with
  `read_waveform`; verify the output ripple sits at `2*fsw`.
- **Averaged model (fast):** for quick DC and AC studies, drive an ideal `1:n` transformer with
  behavioral sources reproducing `<is> = (n*D/2)*<iL>` and `<vD> = (n*D/2)*<Vin>`, feeding the
  `L`-`r_L`-`C`-`r_C`-`R_load` filter. With no switching edges a `.tran` settles almost instantly
  and an `.ac` sweep yields `Gd(s)`/`Gb(s)`/`Zi(s)`/`Zo(s)` directly - confirming the clean
  second-order (no RHP zero) response before the switched run.
