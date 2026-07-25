# Half-bridge converter -- catalog recipe (Track B)

Isolated half-bridge converter stepping 48 V down to about 7.9 V. A capacitive divider
(`CB1`/`CB2` with bleeder resistors) holds the primary return at `Vin/2`; `M1`/`M2` drive the
switch node with complementary gate pulses (D=0.2 per switch at 100 kHz, `VG1` referenced to
the floating source). The 1:1 transformer (`K1 L2 L3 0.9995`) has a primary RC snubber
(`RN1`/`CN1`); the center-free secondary feeds a full-wave rectifier (`D1`-`D4`) and an
`L1`/`C1` filter into a 3.5 ohm load (`.tran 0 2m`).

This recipe was authored clean-room with qspice-mcp schematic tools and validated
end-to-end (netlist, simulation, `V(out)` check) with local QSpice.

## Preflight

1. `describe_server_capabilities` -- QSpice and simulation tools available.
2. `list_workflow_instructions` -- confirm `half-bridge-converter-catalog` is listed.

## Source bundle

Recipe `half_bridge_converter` ships inside qspice-mcp:

- `half_bridge_converter.qsch` -- schematic (source of truth).
- `half_bridge_converter.cir` -- validated netlist, ready to simulate.

## Steps

1. `materialize_reference_circuit(recipe_id="half_bridge_converter")` -- both files in workspace root.
2. `run_simulation(source_path="half_bridge_converter.cir")` -- runs the validated netlist.
3. `measure_waveform(signal="V(out)", operation="mean", t_start=1.6m, t_end=2m)`.

## Success criteria

- Transient completes with no convergence errors.
- Mean `V(out)` over the last 0.4 ms is 7.0-8.8 V (design value ~7.9 V; finite transformer
  leakage costs some duty cycle versus the ideal `2*n*D*Vin/2`).
- `V(mid)` settles at `Vin/2` (24 V) -- confirms the capacitive divider balances.

## If blocked

| Symptom | Action |
| --- | --- |
| Timestep-too-small error | Keep the bundled diode knee smoothing, `K1 < 1`, snubber, and `.options reltol=1m` |
| `V(out)` low | Check `V(mid)` is 24 V and both gate pulses arrive (nets `g1`, `g2`) |
| No `V(out)` | `list_signals`; the output net is named `out` |
| Need edits | Edit the materialized `.qsch` with schematic tools, then `generate_netlist` + `run_simulation` |

- Related topology block: `half_bridge_converter` (see `describe_topology_block` for design equations).
