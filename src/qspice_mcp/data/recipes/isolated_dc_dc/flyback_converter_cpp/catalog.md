# Flyback converter (C++ DLL) — catalog recipe (Track B)

Reproduce the DLL-controlled isolated flyback converter from an **empty workspace** by materializing the bundled reference recipe. Do **not** rebuild the schematic from scratch.

## Preflight

1. `describe_server_capabilities` — QSpice and simulation tools available.
2. `list_workflow_instructions` — confirm `flyback-converter-cpp-catalog` is listed.

## Source bundle

Recipe `flyback_converter_cpp` ships inside qspice-mcp:

- `Flyback_sim.qsch` — flyback power stage + 10-pin `.DLL` block `Flyback_controller` (X1)
- `flyback_controller.cpp` — PWM/sampling control (`flyback_controller` export, duty `D=0.56`)
- `flyback_controller.dll` — prebuilt controller, ready to simulate without a local compiler

**Forbidden:** `create_starter_schematic`, partial `add_component` authoring when `materialize_reference_circuit` is available.

## Steps

1. `materialize_reference_circuit(recipe_id="flyback_converter_cpp")` — confirm all three files in workspace root.
2. `inspect_schematic(schematic_path="Flyback_sim.qsch")` — X1 / `Flyback_controller`, `.tran 0 300µ 0 100n uic`.
3. Optional: `validate_dll_symbol_signature(schematic_path="Flyback_sim.qsch", reference="X1", source_path="flyback_controller.cpp")`.
4. `run_simulation(source_path="Flyback_sim.qsch")` — dry-run then run. When
   `QSPICE_EXE` is set, `generate_netlist` uses companion `QUX.exe -Netlist` so
   the DLL block (X1) is included automatically.
5. `list_signals` → `plot_waveforms` and/or `read_waveform` on `V(out)` (output rail).

## Success criteria

- Transient completes without DLL/subcircuit errors.
- Regulated isolated output voltage waveform is shown.

## If blocked

| Symptom | Action |
| --- | --- |
| DLL fails to load | Rebuild locally: `build_dll_device(source_path="flyback_controller.cpp")` |
| `QSPICE_EXE` not set | Set env var; restart MCP (QUX netlist + simulation need QSpice) |
| `Singular matrix` / undriven gate | Ensure `flyback_controller.dll` exists and netlist includes `X1`; re-run `run_simulation` on `.qsch` after setting `QSPICE_EXE` |
| No `V(out)` | `list_signals`; pick the output net |
| Need edits | Re-materialize; do not author from blank |

Report failing step, tool output, and next action.
