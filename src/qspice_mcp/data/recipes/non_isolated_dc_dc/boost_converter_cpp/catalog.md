# Boost converter (C++ DLL) — catalog recipe (Track B)

Reproduce the DLL-controlled boost converter from an **empty workspace** by materializing the bundled reference recipe. Do **not** rebuild the schematic from scratch.

## Preflight

1. `describe_server_capabilities` — QSpice and simulation tools available.
2. `list_workflow_instructions` — confirm `boost-converter-cpp-catalog` is listed.

## Source bundle

Recipe `boost_converter_cpp` ships inside qspice-mcp:

- `Boost-converter.qsch` — boost power stage (input inductor, low-side switch, output diode) + 10-pin `.DLL` block `Boost_controller` (X1)
- `boost_controller.cpp` — PWM/sampling control (`boost_controller` export, duty `D=0.56` at 200 kHz)
- `boost_controller.dll` — prebuilt controller, ready to simulate without a local compiler

**Forbidden:** `create_starter_schematic`, partial `add_component` authoring when `materialize_reference_circuit` is available.

## Steps

1. `materialize_reference_circuit(recipe_id="boost_converter_cpp")` — confirm all three files in workspace root.
2. `inspect_schematic(schematic_path="Boost-converter.qsch")` — X1 / `Boost_controller`, `.tran 0 300µ 0 100n uic`, `Tsamp=10µ`.
3. Optional: `validate_dll_symbol_signature(schematic_path="Boost-converter.qsch", reference="X1", source_path="boost_controller.cpp")`.
4. `run_simulation(source_path="Boost-converter.qsch")` — dry-run then run. When
   `QSPICE_EXE` is set, `generate_netlist` uses companion `QUX.exe -Netlist` so
   the DLL block (X1) is included automatically.
5. `list_signals` → `plot_waveforms` and/or `read_waveform` on `V(out)` (net `out`).

## Success criteria

- Transient completes without DLL/subcircuit errors.
- Output voltage settles above the input rail (boost action) with switching ripple.

## If blocked

| Symptom | Action |
| --- | --- |
| DLL fails to load | Rebuild locally: `build_dll_device(source_path="boost_controller.cpp")` |
| `QSPICE_EXE` not set | Set env var; restart MCP (QUX netlist + simulation need QSpice) |
| `Singular matrix` / undriven `PWM` | Ensure `boost_controller.dll` exists and netlist includes `X1`; re-run `run_simulation` on `.qsch` after setting `QSPICE_EXE` |
| No `V(out)` | `list_signals`; pick net `out` |
| Need edits | Re-materialize; do not author from blank |

Report failing step, tool output, and next action.
