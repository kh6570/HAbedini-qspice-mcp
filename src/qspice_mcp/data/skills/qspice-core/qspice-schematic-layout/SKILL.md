---
name: qspice-schematic-layout
description: Place schematic components readably without overlap — use suggest_component_placement, add_component auto_place, or apply_schematic_layout_spec for batch JSON specs; keep parts upright (0° rotation), and follow workflow coordinate tables for complex circuits like buck converters.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.5"
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
5. Nudge mistakes with **`set_component_position`** — the unified placement tool that
   moves **and/or** rotates (pass `rotation_degrees`, multiples of 45°). It preserves
   attached connections and normalizes refdes/value text by default (see below).
6. Spot-check connectivity with **`inspect_schematic`** before simulating.

## Wired components: move / rotate keep the circuit intact by default

**`set_component_position` is the one tool you need.** It moves and/or rotates a part,
and **by default**:

- **`preserve_connections=true`** — attached wire endpoints, junctions, and net labels
  follow the moved/rotated pins automatically (QSpice GUI drag parity). No manual
  `remove_wire`/`add_wire` refresh needed.
- **`normalize_text=true`** — refdes/value symbol text is reset to upright,
  left-to-right readability, compensating for the body rotation.

```text
set_component_position(schematic_path="filter.qsch", reference="R1",
                       position_x=1600, position_y=1200)
→ R1 moves; attached VIN/VOUT wires follow; labels stay readable
→ result.rewired_endpoints and result.normalized_text_count report what changed
```

**Opt-outs (rare):**

- `preserve_connections=false` — move the symbol only (legacy behavior); you then own
  the `remove_wire`/`add_wire` refresh.
- `normalize_text=false` — leave text rotation untouched.

**Deprecated aliases** (still work, slated for removal): `set_component_rotation`
(rotation only) and `move_component_preserving_connections` both delegate to
`set_component_position`. Prefer the unified tool.

**Still prefer place → wire order** when building from scratch: finalize
`(position_x, position_y, rotation_degrees)`, then `add_wire` using **pin selectors**
(`start_reference` + `start_pin`). Default-on preservation is for *edits to an already
wired part*, not a substitute for clean initial wiring.

## Symbol rotation vs readable text (refdes / value)

Rotating the **symbol body** via `set_component_position(rotation_degrees=…)` (or
`rotation_degrees` on `add_component`) is OK when topology or pin direction needs it.
Embedded **refdes and value text rotate with the symbol**, but `set_component_position`
normalizes them back to upright by default (`normalize_text=true`).

**Target for human-readable labels:** horizontal, left-to-right, upright — same as
default `0°` placement.

**When you need a standalone text fix-up** (e.g. `normalize_text=false` was used, or
text was authored crooked):

1. Call **`normalize_component_text_rotation`** per ref (default compensates body
   rotation so labels read horizontal in world space).
2. Optionally pass `text_roles=["reference", "value"]` (or `refdes` alias) to limit
   which embedded text rows are updated.
3. Use **`read_component_symbol`** to verify `text_attributes` if the sheet is dense.
4. For manual per-item layout (position, size, explicit rotation), use
   **`set_component_symbol_text`** with `text_role="reference"` or `"value"`.
5. Do **not** change refdes string content through symbol-text tools — use
   **`rename_component_reference`** for renames.

**Order of operations:** `set_component_position` handles move → wire-follow → text
normalization in one call; verify in GUI if the sheet is dense.

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

## Example (rotate a wired part)

```text
set_component_position(schematic_path="filter.qsch", reference="R1", rotation_degrees=90)
→ R1 rotates; attached wires/junctions/net labels follow the pins (preserve_connections)
→ refdes/value text reset upright (normalize_text); no manual wire refresh needed

# Standalone text fix-up only if you opted out of normalize_text:
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
- Passing `preserve_connections=false` on a wired edit and then forgetting the manual
  **`remove_wire` / `add_wire`** refresh — breaks connectivity while the drawing still looks fine
- Reaching for deprecated `set_component_rotation` / `move_component_preserving_connections`
  instead of the unified **`set_component_position`**
- Ignoring `read_workflow_instruction` coordinate tables for the full buck converter
- Skipping `read_component` verification after large automated edits

## Related tools

- `normalize_component_text_rotation` — upright refdes/value after symbol body rotation
- `read_component_symbol` / `set_component_symbol_text` — inspect or manually tweak text layout
- `describe_schematic_layout_spec` / `apply_schematic_layout_spec` — batch JSON placement
- `read_workflow_instruction(instruction_id="buck-converter-cpp")` — full coordinate tables
- `inspect_schematic` — topology summary (not placement audit)
- `list_components` — ref list only; use `read_component` for coordinates
