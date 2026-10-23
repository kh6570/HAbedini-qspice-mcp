In the name of God, the Most Gracious, the Most Merciful

# Placement

## Preferred workflow

1. **`describe_topology_authoring_support`** — confirm layout tools are available.
2. For each new part (unless copying coordinates from a workflow table):
   - Call **`suggest_component_placement`** with `schematic_path` and `component_kind`, **or**
   - Call **`add_component`** with **`auto_place=true`** (same grid logic), **or**
   - For a known set of parts, call **`describe_schematic_layout_spec`**, write a v1 JSON file under the workspace, and batch-apply with **`apply_schematic_layout_spec`**.
3. Use the returned `position_x`, `position_y`, and `rotation_degrees` (default **0**).
4. After a batch of placements, spot-check with **`read_component`** on key refs.
5. Nudge mistakes with **`set_component_position`** — the unified placement tool that moves **and/or** rotates (pass `rotation_degrees`, multiples of 45°). It preserves attached connections and normalizes refdes/value text by default (see `wired-edits.md`).
6. Spot-check connectivity with **`inspect_schematic`** before simulating.

## Layout rules

| Rule | Detail |
| --- | --- |
| Grid | Server scans **900×500** schematic units, **left-to-right**, then next row down |
| Rotation | Default **0°** on the symbol for new parts. Rotate the body only when topology requires it; `set_component_position` normalizes text upright by default (no separate call needed unless you opt out) |
| Overlap | Never place multiple parts at `(0,0)` or reuse the same coordinates; collision boxes include refdes/value text margin |
| GND wiring | Place each `ground` symbol **on the negative pin** (same point as `V−` / `C−`). Use `net_name="0"` or default GND. Do **not** hang GND below the part on a dangling wire — QSpice reports *no ground* when the GND triangle is not on node `0` |
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
