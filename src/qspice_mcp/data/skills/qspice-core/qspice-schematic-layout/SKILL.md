---
name: qspice-schematic-layout
description: Place schematic components readably without overlap — use suggest_component_placement, add_component auto_place, or apply_schematic_layout_spec for batch JSON specs; keep parts upright (0° rotation), and follow workflow coordinate tables for complex circuits like buck converters.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.1"
---

# QSpice: Schematic Layout

How to place parts so a `.qsch` stays readable for humans: no stacked symbols,
upright refdes/value text, and left-to-right signal flow when building ad-hoc
topology.

## When to use this skill

- Track A scratch authoring with `add_component`, `add_dll_block`, wires, and labels
- Any time the agent would guess `(position_x, position_y)` coordinates
- Before reporting a schematic as "complete" to the user

## Preferred workflow

1. **`describe_topology_authoring_support`** — confirm layout tools are available.
2. For each new part (unless copying coordinates from a workflow table):
   - Call **`suggest_component_placement`** with `schematic_path` and `component_kind`, **or**
   - Call **`add_component`** with **`auto_place=true`** (same grid logic), **or**
   - For a known set of parts, call **`describe_schematic_layout_spec`**, write a v1 JSON
     file under the workspace, and batch-apply with **`apply_schematic_layout_spec`**.
3. Use the returned `position_x`, `position_y`, and `rotation_degrees` (default **0**).
4. After a batch of placements, spot-check with **`read_component`** on key refs.
5. Nudge mistakes with **`set_component_position`**; use **`set_component_rotation`**
   only when the workflow table or topology requires it (multiples of 45°).

## Layout rules

| Rule | Detail |
| --- | --- |
| Grid | Server scans **400×400** schematic units, **left-to-right**, then next row down |
| Rotation | Default **0°** (upright text). Do not rotate "for neatness" alone |
| Overlap | Never place multiple parts at `(0,0)` or reuse the same coordinates; collision boxes include refdes/value text margin |
| GND wiring | Do **not** draw one long horizontal GND wire through a vertical R/C bottom pin — use separate GND symbols at V− and the load |
| Complex circuits | For buck/boost scratch builds, **follow `read_workflow_instruction` tables** — they override the auto grid |
| Dense edits | Auto placement uses conservative footprints; open the GUI to fine-tune if needed |

## Example (layout spec batch)

```text
describe_schematic_layout_spec()
→ copy/adapt example_document to workspace (e.g. power_stage.v1.json)

apply_schematic_layout_spec(
  schematic_path="buck.qsch",
  spec_path="power_stage.v1.json",
)
→ places L1/M1/M2/B1 with collision-aware auto rows; add wires/labels separately
```

Bundled reference: `scratch_power_stage.v1.json` (compact power-stage rows only).

## Example (auto placement)

```text
suggest_component_placement(
  schematic_path="buck.qsch",
  component_kind="inductor",
)
→ use returned position_x, position_y, rotation_degrees=0 in add_component

add_component(
  schematic_path="buck.qsch",
  component_kind="nmos",
  reference="M1",
  value="BSC123N08NS3",
  auto_place=true,
)
```

## Anti-patterns

- Placing every part at default `(0, 0)` — they stack invisibly
- Rotating all MOSFETs 90° without a workflow reason — wires and labels become harder to read
- Ignoring `read_workflow_instruction` coordinate tables for the full buck converter
- Skipping `read_component` verification after large automated edits

## Related tools

- `describe_schematic_layout_spec` / `apply_schematic_layout_spec` — batch JSON placement
- `read_workflow_instruction(instruction_id="buck-converter-cpp")` — full coordinate tables
- `inspect_schematic` — topology summary (not placement audit)
- `list_components` — ref list only; use `read_component` for coordinates
