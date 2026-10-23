In the name of God, the Most Gracious, the Most Merciful

# First circuit

## Track B — start from a bundled reference recipe (preferred when one fits)

1. `list_reference_circuit_recipes` — see available canonical circuits (id + title).
2. `describe_reference_circuit_recipe` — read one recipe's manifest, file list, and topology digest to confirm it matches the goal.
3. `materialize_reference_circuit` — copy the recipe's `.qsch` (+ sidecars like a C++ DLL source) into the workspace.
4. Optional: `list_workflow_instructions` → `read_workflow_instruction` for a step-by-step build/run prompt tied to that recipe.

## Track A — author from scratch (when no recipe fits)

1. `describe_topology_authoring_support` — check what scratch authoring supports.
2. `create_starter_schematic` (runnable source+load in one call) or `create_schematic` (blank) to begin.
3. Build topology: `add_component` (`R/C/D/V/L/B/nmos/pmos` or `GND`; use `auto_place=true` or `suggest_component_placement` for readable grids), `add_wire`, `add_junction`, `add_net_label`; adjust with `set_component_value`, `set_component_parameters`, `set_component_position`.
4. For custom devices, `write_workspace_text_file` writes a `.c`/`.cpp` source and auto-builds the sibling `.dll` (see the mixed-signal/DLL skill).

Install the **`qspice-schematic-layout`** skill when authoring scratch topology so placement stays collision-free and upright.

## Inspect what you have

- `inspect_schematic` — summary of a `.qsch` and the analyses it defines.
- `list_components`, `list_subcircuits`, `read_component` — enumerate and drill in.
- `describe_edit_capability` — preflight: map an edit intent to the right tool with a go/no-go answer before mutating.
