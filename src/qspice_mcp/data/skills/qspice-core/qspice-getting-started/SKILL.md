---
name: qspice-getting-started
description: Drive the QSpice MCP server end to end — discover or author a circuit, generate a netlist, run a simulation, and read or measure waveforms. Use when starting any QSpice task, when unsure which tool to call, when asked to simulate a circuit, build a buck/boost or other topology, inspect a .qsch, or read simulation results.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Getting Started

`.qsch` is the source of truth. Netlists, logs, and waveforms are derived.
`read_waveform` stays inside its point budget. Call
`describe_server_capabilities` before treating a tool as broken. Paths resolve
inside the server workspace.

## When to use

Use this when starting a QSpice task, when you are unsure which tool to call,
or when asked to simulate a circuit, inspect a `.qsch`, or read a result.

## When not to use

Do not use this for placement grids, converter characterization, DLL authoring,
waveform math, or convergence repair. Those optional skills are
`qspice-schematic-layout`, `qspice-power-electronics`,
`qspice-mixed-signal-dll`, `qspice-waveform-analysis`, and
`qspice-convergence-debugging`.

## Reference files

Open a file only when that step is needed:

- `mental-model.md` — source of truth, staged siblings, and budgets
- `first-circuit.md` — recipes, scratch authoring, and inspection
- `simulate-and-read.md` — netlist, prepare, run, log, and measure
- `sweep.md` — one-parameter batch sweeps
- `tolerance.md` — Monte Carlo and worst-case spread
