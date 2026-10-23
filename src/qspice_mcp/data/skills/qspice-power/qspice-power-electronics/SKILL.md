---
name: qspice-power-electronics
description: Simulate and characterize switching power converters in QSpice. Use for buck/boost/SMPS work — staging transient and AC analyses, measuring efficiency and step response, and assessing loop gain, phase margin, and gain margin for stability.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Power Electronics

Switching converters need a working transient first, then efficiency, load-step
response, and control-loop stability. `.qsch` stays the source of truth.

## When to use

Use this when designing or analyzing a DC-DC converter or other switching power
stage, and when the result must include efficiency, ripple, load-step, or
phase-margin numbers.

## When not to use

Do not use this when the run fails to converge. Open
`qspice-convergence-debugging` first. For a generic single-node metric, open
`qspice-waveform-analysis`.

## Reference files

- `workflow.md` — transient, efficiency, step response, and sanity checks
- `bode.md` — closed-loop `.bode` injection, settling, and amplitude
- `buck-from-scratch.md` — author a buck from the prompt targets
- `loop-gain.md` — phase margin, gain margin, and `.meas fra` check
