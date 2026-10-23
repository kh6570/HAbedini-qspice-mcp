In the name of God, the Most Gracious, the Most Merciful

# Wired edits and readable text

## Wired components: move / rotate keep the circuit intact by default

**`set_component_position` is the one tool you need.** It moves and/or rotates a part, and **by default**:

- **`preserve_connections=true`** — attached wire endpoints, junctions, and net labels follow the moved/rotated pins automatically (QSpice GUI drag parity). No manual `remove_wire`/`add_wire` refresh needed.
- **`normalize_text=true`** — refdes/value symbol text is reset to upright, left-to-right readability, compensating for the body rotation.

```text
set_component_position(schematic_path="filter.qsch", reference="R1",
                       position_x=1600, position_y=1200)
→ R1 moves; attached VIN/VOUT wires follow; labels stay readable
→ result.rewired_endpoints and result.normalized_text_count report what changed
```

**Opt-outs (rare):**

- `preserve_connections=false` — move the symbol only (legacy behavior); you then own the `remove_wire`/`add_wire` refresh.
- `normalize_text=false` — leave text rotation untouched.

The former `set_component_rotation` and `move_component_preserving_connections` aliases were removed; `set_component_position` is the single placement tool.

**Still prefer place → wire order** when building from scratch: finalize `(position_x, position_y, rotation_degrees)`, then `add_wire` using **pin selectors** (`start_reference` + `start_pin`). Default-on preservation is for *edits to an already wired part*, not a substitute for clean initial wiring.

## Symbol rotation vs readable text (refdes / value)

Rotating the **symbol body** via `set_component_position(rotation_degrees=…)` (or `rotation_degrees` on `add_component`) is OK when topology or pin direction needs it. Embedded **refdes and value text rotate with the symbol**, but `set_component_position` normalizes them back to upright by default (`normalize_text=true`).

**Target for human-readable labels:** horizontal, left-to-right, upright — same as default `0°` placement.

**When you need a standalone text fix-up** (for example `normalize_text=false` was used, or text was authored crooked):

1. Call **`normalize_component_text_rotation`** per ref (default compensates body rotation so labels read horizontal in world space).
2. Optionally pass `text_roles=["reference", "value"]` (or `refdes` alias) to limit which embedded text rows are updated.
3. Use **`read_component_symbol`** to verify `text_attributes` if the sheet is dense.
4. For manual per-item layout (position, size, explicit rotation), use **`set_component_symbol_text`** with `text_role="reference"` or `"value"`.
5. Do **not** change refdes string content through symbol-text tools — use **`rename_component_reference`** for renames.

**Order of operations:** `set_component_position` handles move → wire-follow → text normalization in one call; verify in GUI if the sheet is dense.

## Example (rotate a wired part)

```text
set_component_position(schematic_path="filter.qsch", reference="R1", rotation_degrees=90)
→ R1 rotates; attached wires/junctions/net labels follow the pins (preserve_connections)
→ refdes/value text reset upright (normalize_text); no manual wire refresh needed

# Standalone text fix-up only if you opted out of normalize_text:
normalize_component_text_rotation(schematic_path="filter.qsch", reference="R1")
→ refdes/value text readable horizontal; skips factory defaults at 0° body
```
