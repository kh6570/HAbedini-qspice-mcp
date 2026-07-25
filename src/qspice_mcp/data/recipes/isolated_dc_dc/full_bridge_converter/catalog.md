# Full-bridge converter -- catalog recipe (Track B)

Isolated full-bridge (H-bridge) converter stepping 48 V down to about 7.4 V. Four NMOS
switches drive the primary in diagonal pairs (`M1`+`M2`, then `M3`+`M4`, D=0.175 per pair at
100 kHz; high-side gate drives are referenced to the floating sources). The 2:1 transformer
(`K1 L2 L3 0.9995`, primary 2 mH, secondary 500 uH) carries a primary RC snubber
(`RN1`/`CN1`); the secondary feeds a full-wave rectifier (`D1`-`D4`) and an `L1`/`C1` filter
into a 3.5 ohm load (`.tran 0 2m`).

This recipe was authored clean-room with qspice-mcp schematic tools and validated
end-to-end (netlist, simulation, `V(out)` check) with local QSpice.

## Preflight

1. `describe_server_capabilities` -- QSpice and simulation tools available.
2. `list_workflow_instructions` -- confirm `full-bridge-converter-catalog` is listed.

## Source bundle

Recipe `full_bridge_converter` ships inside qspice-mcp:

- `full_bridge_converter.qsch` -- schematic (source of truth).
- `full_bridge_converter.cir` -- validated netlist, ready to simulate.

## Steps

1. `materialize_reference_circuit(recipe_id="full_bridge_converter")` -- both files in workspace root.
2. `run_simulation(source_path="full_bridge_converter.cir")` -- runs the validated netlist.
3. `measure_waveform(signal="V(out)", operation="mean", t_start=1.6m, t_end=2m)`.

## Success criteria

- Transient completes with no convergence errors.
- Mean `V(out)` over the last 0.4 ms is 7.0-8.8 V (design value ~7.4 V; ideal
  `2*n*D*Vin` minus rectifier drops and leakage duty loss).
- `V(swa)` and `V(swb)` alternate between rails with the expected phase shift.

## If blocked

| Symptom | Action |
| --- | --- |
| Timestep-too-small error | Keep the bundled diode knee smoothing, `K1 < 1`, snubber, and `.options reltol=1m` |
| `V(out)` low | Confirm diagonal gate pairing: `VG1`/`VG2` fire together, `VG3`/`VG4` half a period later |
| No `V(out)` | `list_signals`; the output net is named `out` |
| Need edits | Edit the materialized `.qsch` with schematic tools, then `generate_netlist` + `run_simulation` |

- Related topology block: `full_bridge_converter` (see `describe_topology_block` for design equations).
