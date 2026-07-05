# Buck converter (C++ DLL) — catalog recipe (Track B)

Reproduce the DLL-controlled buck converter from an **empty workspace** by materializing the bundled reference recipe. Do **not** rebuild the schematic from scratch.

**Track A alternative:** `read_workflow_instruction(instruction_id="buck-converter-cpp")` — authoring tools only.

## Preflight

1. `describe_server_capabilities` — QSpice and simulation tools available.
2. `list_workflow_instructions` — confirm `buck-converter-cpp-catalog` is listed.

## Source bundle

Recipe `buck_converter_cpp` ships inside qspice-mcp:

- `Buck-converter.qsch` — power stage + 10-pin `.DLL` block `Buck_controller` (X1)
- `buck_controller.cpp` — PWM/sampling control (`buck_controller` export, duty `D=0.56`)

**Forbidden:** `create_starter_schematic`, partial `add_component` authoring when `materialize_reference_circuit` is available.

## Steps

1. `materialize_reference_circuit(recipe_id="buck_converter_cpp")` — confirm both files in workspace root.
2. `build_dll_device(source_path="buck_controller.cpp")` — confirm `buck_controller.dll` beside schematic.
3. `inspect_schematic(schematic_path="Buck-converter.qsch")` — X1 / `Buck_controller`, `.tran 0 300µ 0 100n uic`, `Tsamp=10µ`.
4. Optional: `validate_dll_symbol_signature(schematic_path="Buck-converter.qsch", reference="X1", source_path="buck_controller.cpp")`.
5. `run_simulation(source_path="Buck-converter.qsch")` — dry-run then run. When
   `QSPICE_EXE` is set, `generate_netlist` uses companion `QUX.exe -Netlist` so
   the DLL block (X1) is included automatically.
6. `list_signals` → `plot_waveforms` and/or `read_waveform` on `V(out)` (net `out`).

## Success criteria

- Transient completes without DLL/subcircuit errors.
- Output voltage waveform shown; ~5–6 V steady state with ripple.

## If blocked

| Symptom | Action |
| --- | --- |
| Missing DLL | Re-run `build_dll_device` |
| `QSPICE_EXE` not set | Set env var; restart MCP (QUX netlist + simulation need QSpice) |
| `Singular matrix` / undriven `PWM` | Ensure `buck_controller.dll` exists and netlist includes `X1`; re-run `run_simulation` on `.qsch` after setting `QSPICE_EXE` |
| No `V(out)` | `list_signals`; pick net `out` |
| Need edits | Re-materialize; do not author from blank |

Report failing step, tool output, and next action.
