---
name: qspice-schematic-layout
description: Place schematic components readably without overlap — use suggest_component_placement, add_component auto_place, or apply_schematic_layout_spec for batch JSON specs; keep parts upright (0° rotation), and follow workflow coordinate tables for complex circuits like buck converters.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.6"
---
In the name of God, the Most Gracious, the Most Merciful

# QSpice: Schematic Layout

Place parts so a `.qsch` stays readable: no stacked symbols, upright refdes
and value text, and left-to-right signal flow. `.qsch` stays the source of
truth; do not place parts on a staged `*-tran.qsch`.

## When to use

Use this for scratch authoring with `add_component`, `add_dll_block`, wires,
and labels, whenever coordinates would otherwise be guessed, and before
reporting a schematic as complete.

## When not to use

Do not use this to run a simulation, interpret a waveform, author a DLL, or
debug convergence. Use `qspice-getting-started`, `qspice-waveform-analysis`,
`qspice-mixed-signal-dll`, or `qspice-convergence-debugging` for those.

## Reference files

- `placement.md` — grid, auto-place, layout spec, and placement rules
- `wired-edits.md` — move/rotate keeps wires, and upright refdes text
- `staged-schematics.md` — `*-tran.qsch` siblings and anti-patterns
