---
name: qspice-mixed-signal-dll
description: Author, scaffold, build, and validate QSpice `.DLL` custom-device blocks for mixed-signal C/C++ models. Use when adding a controller or behavioral block backed by compiled code, generating a C++ scaffold from a symbol, building the DLL, or checking that a symbol matches its source.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Mixed-Signal `.DLL` Custom Devices

QSpice runs compiled C/C++ models as `.DLL` custom-device blocks. The symbol is
the contract: pin names in the symbol must match the source port list.

## When to use

Use this when a circuit needs a controller, state machine, or behavioral block
that is easier in code than in SPICE primitives, or when a symbol and its C++
source must be checked against each other.

## When not to use

Do not use this for pure analog placement. Open `qspice-getting-started` and
`qspice-schematic-layout`. If the simulation runs but will not converge, open
`qspice-convergence-debugging`.

## Reference files

- `workflow.md` — device spec, manual pins, scaffold, build, and validate
- `symbol-reuse.md` — export and place standalone `.qsym` symbols
