---
name: qspice-power-electronics
description: Simulate and characterize switching power converters in QSpice. Use for buck/boost/SMPS work — staging transient and AC analyses, measuring efficiency and step response, and assessing loop gain, phase margin, and gain margin for stability.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.0"
---

# QSpice: Power Electronics

A workflow for switching converters (buck, boost, SMPS): get a working
transient, then characterize efficiency, transient response, and control-loop
stability.

## When to use

- Designing or analyzing a DC-DC converter or other switching power stage.
- You need efficiency, output ripple, load-step response, or loop-gain /
  phase-margin numbers — not just "does it run."

## When NOT to use

- The run won't converge or stops early → `qspice-convergence-debugging` first.
- Generic single-node waveform reads/metrics → `qspice-waveform-analysis`.

## Workflow

1. **Get a circuit.** `materialize_reference_circuit` for a bundled starting point
   (e.g. `buck_converter_cpp`), or author your own. `inspect_schematic` to confirm
   topology; `check_schematic` for a conservative ERC pass (floating nets,
   single-pin nets, missing ground) before spending sim time.
2. **Transient first.** `prepare_transient` to stage a `.tran` directive long
   enough to reach steady state plus the events you care about, then
   `run_simulation`.
3. **Characterize the output.** `read_waveform` on the switching node and output;
   `measure_step_response` for rise time / overshoot / settling on a load or
   reference step; `measure_efficiency` from input/output power traces.
4. **Assess the loop.** For a switched (non-averaged) SMPS prefer `.bode`:
   `prepare_bode_analysis` on the settled circuit, `run_simulation`, then
   `measure_stability_margins`. For small-signal/averaged models use
   `prepare_loop_gain_analysis` (Tian or Middlebrook injection) + `prepare_ac`.
5. **Verify suspicious Bode points.** `.bode` uses aggressive numerical methods
   and can carry artifacts (spectral leakage, aperture diffraction). Spot-check
   the crossover with `prepare_meas(kind="fra", ...)` — it stages
   `.meas <name> fra <freq> <input> <output>`, the most reliable frequency-domain
   measurement QSpice offers — then re-run and `read_measures`.

## Closed-loop `.bode` details

- **Injection point:** the perturbing source goes between the SMPS output and
  the top of the feedback divider (low impedance driving high impedance).
- **Settling first:** run `prepare_transient` + `run_simulation` to learn how
  long the supply takes to settle; pass that as `settling_time` to
  `prepare_bode_analysis`. No settling acceleration is attempted by QSpice.
- **Reference node:** if the feedback reference is not at AC ground, pass
  `reference_node` (stages `.options boderef=<node>` alongside `.bode`).
- **Amplitude shaping:** perturbation amplitude rises away from the geometric
  mean of the sweep by default. Tune with `bode_amplitude_frequency`,
  `bode_low_power`, and `bode_high_power` (`.options bodeampfreq/bodelopow/bodehipow`),
  or set `bode_amplitude_frequency="0"` for constant amplitude.
- **Low FSTART is expensive:** each decade down multiplies simulation time.

## What "good" looks like

| Metric | Tool | Sanity check |
| --- | --- | --- |
| Regulation | `read_waveform` / `measure_waveform` | `V(out)` settles near target |
| Ripple | `read_waveform` | Output ripple within spec at steady state |
| Efficiency | `measure_efficiency` | Pout/Pin physical (<1), losses reasonable |
| Transient | `measure_step_response` | Bounded overshoot, settles, no sustained ring |
| Stability | `measure_stability_margins` | Phase margin typically ≥ 45°, positive gain margin |

## Conventions

- Simulate to steady state before measuring ripple/efficiency — early transient
  windows skew averages.
- Run `check_schematic` before long transient sweeps; a floating feedback node is
  cheaper to catch statically than after a failed multi-second run.
- For loop gain, keep the injection method consistent between staging and
  margin measurement.
- Long switching transients produce huge `.qraw` files; `prepare_save` stages a
  `.save` directive (wildcards supported) to keep only the traces you need.
- `.options savepowers=1` (via `prepare_options`) records per-device dissipation
  for loss breakdowns without manual V×I expressions.
