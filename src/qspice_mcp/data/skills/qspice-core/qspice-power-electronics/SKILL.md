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
4. **Assess the loop.** `prepare_loop_gain_analysis` (Tian or Middlebrook
   injection) + `prepare_ac`, run, then `measure_stability_margins` for crossover
   frequency, phase margin, and gain margin.

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
