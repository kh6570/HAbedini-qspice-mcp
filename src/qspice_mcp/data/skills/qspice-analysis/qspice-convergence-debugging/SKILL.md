---
name: qspice-convergence-debugging
description: Diagnose and fix QSpice simulations that fail to converge, stop early, or produce no usable waveform. Use when a run errors, the log shows "no convergence", "timestep too small", singular-matrix, or gmin-stepping failures, or when V(out) is missing/flat after a simulation.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Convergence Debugging

Convergence failures are about the numerics and the circuit, not the MCP
server. Read the log before changing anything, and change one factor at a time.

## When to use

Use this when `run_simulation` errors, the waveform is missing or short, or
`read_log` reports no convergence, timestep too small, a singular matrix,
gmin stepping failed, or an iteration limit.

## When not to use

Do not use this for `connected=false`, a missing `QSPICE_EXE`, or a
backend-unavailable error. Call `describe_server_capabilities` for setup
problems.

## Reference files

- `workflow.md` — read the log, form one hypothesis, and re-run
- `options.md` — `.options` starting points and QSpice convergence knobs
