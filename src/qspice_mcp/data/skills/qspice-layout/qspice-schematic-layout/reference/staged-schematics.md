In the name of God, the Most Gracious, the Most Merciful

# Staged schematics and anti-patterns

## Staged schematics (`*-tran.qsch`, `*-ac.qsch`, …)

`prepare_transient` and other `prepare_*` tools copy **`source_path`** to a sibling `output_path` and append one analysis directive. That sibling is for **simulation only**, not layout editing.

| Do | Don't |
| --- | --- |
| Edit placement on `my_circuit.qsch` | Open `my_circuit-tran.qsch` in the GUI to move parts |
| Re-run `prepare_transient` after layout changes | Assume `-tran` tracks GUI edits on the base file |
| `run_simulation(source_path="…-tran.qsch")` | Use `-tran` as the real schematic in reports |

If the base schematic looks good but `-tran` looks stacked or stale, the staged copy is out of date — refresh with `prepare_*` from the current base, don't re-layout inside `-tran`.

## Anti-patterns

- Placing every part at default `(0, 0)` — they stack invisibly
- Treating `*-tran.qsch` as the editable master schematic
- Passing `preserve_connections=false` on a wired edit and then forgetting the manual **`remove_wire` / `add_wire`** refresh — breaks connectivity while the drawing still looks fine
- Reaching for the removed `set_component_rotation` / `move_component_preserving_connections` names instead of the unified **`set_component_position`**
- Ignoring `read_workflow_instruction` coordinate tables for the full buck converter
- Skipping `read_component` verification after large automated edits

## Related tools

- `normalize_component_text_rotation` — upright refdes/value after symbol body rotation
- `read_component_symbol` / `set_component_symbol_text` — inspect or manually tweak text layout
- `describe_schematic_layout_spec` / `apply_schematic_layout_spec` — batch JSON placement
- `add_library_component` — clone a symbol from a template `.qsch` (parts beyond the built-in kinds)
- `export_symbol_to_qsym` / `add_component_from_qsym` — reuse symbols as standalone `.qsym` files
- `render_schematic_image` — PNG preview of the sheet to eyeball placement without the GUI
- `check_schematic` — quick ERC pass (floating nets, missing ground) before simulating
- `read_workflow_instruction(instruction_id="buck-converter-cpp")` — full coordinate tables
- `inspect_schematic` — topology summary (not placement audit)
- `list_components` — ref list only; use `read_component` for coordinates
