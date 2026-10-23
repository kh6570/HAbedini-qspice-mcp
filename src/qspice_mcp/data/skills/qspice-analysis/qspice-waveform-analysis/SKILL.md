---
name: qspice-waveform-analysis
description: Inspect, derive, and measure QSpice waveform results after a simulation. Use when reading signals from a `.qraw`, comparing nodes, computing derived expressions like V(out)-V(in), measuring RMS/peak/gain/THD, or exporting traces for further analysis.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Waveform Analysis

Turn a completed `.qraw` into answers: which signals exist, what a derived
quantity looks like, and which scalar metrics describe it. QSpice lowercases
net names, so list signals before reading them.

## When to use

Use this after a simulation finishes and you need a trace, a derived signal
such as `V(out)-V(in)`, or a scalar such as RMS, gain, or THD.

## When not to use

Do not use this when the run failed or produced no waveform. Open
`qspice-convergence-debugging`. If the circuit still needs to be authored or
simulated, open `qspice-getting-started`.

## Reference files

- `workflow.md` — list, read, derive, measure, Fourier, Bode, and export
