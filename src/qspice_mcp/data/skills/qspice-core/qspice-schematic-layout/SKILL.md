---
name: qspice-schematic-layout
description: Place schematic components readably without overlap — use suggest_component_placement, add_component auto_place, or apply_schematic_layout_spec for batch JSON specs; keep parts upright (0° rotation), and follow workflow coordinate tables for complex circuits like buck converters.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.4"
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
6. **After any move or rotate on a wired part**, refresh connections (see below) before simulating.

## Wired components: move / rotate without breaking the circuit

**Today:** `set_component_position` and `set_component_rotation` move the symbol only.
Existing wire segments keep their old `(x, y)` endpoints — they do **not** follow pins
automatically. Netlist connectivity can silently break if endpoints no longer meet pins.

**Before editing placement**

- Prefer **place → wire** order: finalize `(position_x, position_y, rotation_degrees)`
  with `add_component` / `auto_place`, then `add_wire` using **pin selectors**
  (`start_reference` + `start_pin`, not raw coordinates alone).

**After `set_component_position` or `set_component_rotation` on a connected ref**

1. **`read_component`** — note new pin geometry and `rotation_degrees`.
2. For each affected net: **`remove_wire`** on the stale segment (pin selectors or
   coordinates), then **`add_wire`** again with the same `net_name` and updated
   pin selectors so endpoints land on the moved pins.
3. Re-run **`inspect_schematic`** or spot-check key refs; only then **`run_simulation`**.

**Do not** assume wires stayed attached because the schematic still looks connected in
a quick glance — floating or mis-joined segments are a common failure mode after layout nudges.

## Symbol rotation vs readable text (refdes / value)

Rotating the **symbol body** with `set_component_rotation` (or `rotation_degrees` on
`add_component` / `set_component_position`) is OK when topology or pin direction needs
it. Embedded **refdes and value text rotate with the symbol** unless you fix them.

**Target for human-readable labels:** horizontal, left-to-right, upright — same as
default `0°` placement.

**After a layout pass that rotated any refs**

1. Call **`normalize_component_text_rotation`** per rotated ref (default compensates
   body rotation so labels read horizontal in world space).
2. Optionally pass `text_roles=["reference", "value"]` (or `refdes` alias) to limit
   which embedded text rows are updated.
3. Use **`read_component_symbol`** to verify `text_attributes` if the sheet is dense.
4. For manual per-item layout (position, size, explicit rotation), use
   **`set_component_symbol_text`** with `text_role="reference"` or `"value"`.
5. Do **not** change refdes string content through symbol-text tools — use
   **`rename_component_reference`** for renames.

**Order of operations:** finalize symbol position/rotation → refresh wires →
**normalize text rotation** → verify in GUI if the sheet is dense.

## Layout rules

| Rule | Detail |
| --- | --- |
| Grid | Server scans **900×500** schematic units, **left-to-right**, then next row down |
| Rotation | Default **0°** on the symbol for new parts. Rotate the body only when topology requires it; call **`normalize_component_text_rotation`** afterward |
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

## Example (text after rotate)

```text
set_component_rotation(schematic_path="filter.qsch", reference="R1", rotation_degrees=90)
→ refresh wires on R1 if already connected

normalize_component_text_rotation(schematic_path="filter.qsch", reference="R1")
→ refdes/value text readable horizontal; skips factory defaults at 0° body
```

## Staged schematics (`*-tran.qsch`, `*-ac.qsch`, …)

`prepare_transient` and other `prepare_*` tools copy **`source_path`** to a sibling
`output_path` and append one analysis directive. That sibling is for **simulation
only**, not layout editing.

| Do | Don't |
| --- | --- |
| Edit placement on `my_circuit.qsch` | Open `my_circuit-tran.qsch` in the GUI to move parts |
| Re-run `prepare_transient` after layout changes | Assume `-tran` tracks GUI edits on the base file |
| `run_simulation(source_path="…-tran.qsch")` | Use `-tran` as the “real” schematic in reports |

If the base schematic looks good but `-tran` looks stacked or stale, the staged
copy is out of date — refresh with `prepare_*` from the current base, don't
re-layout inside `-tran`.

## Anti-patterns

- Placing every part at default `(0, 0)` — they stack invisibly
- Treating `*-tran.qsch` as the editable master schematic
- Rotating symbol bodies for “neatness” without calling **`normalize_component_text_rotation`**
- Moving or rotating a wired part without **`remove_wire` / `add_wire`** refresh — breaks connectivity while the drawing still looks fine
- Ignoring `read_workflow_instruction` coordinate tables for the full buck converter
- Skipping `read_component` verification after large automated edits

## Related tools

- `normalize_component_text_rotation` — upright refdes/value after symbol body rotation
- `read_component_symbol` / `set_component_symbol_text` — inspect or manually tweak text layout
- `describe_schematic_layout_spec` / `apply_schematic_layout_spec` — batch JSON placement
- `read_workflow_instruction(instruction_id="buck-converter-cpp")` — full coordinate tables
- `inspect_schematic` — topology summary (not placement audit)
- `list_components` — ref list only; use `read_component` for coordinates
