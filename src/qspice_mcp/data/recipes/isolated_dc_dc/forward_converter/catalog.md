# Forward converter -- catalog recipe (Track B)

Single-switch forward converter stepping 48 V down to about 9.2 V. Transformer is three
coupled inductors (`K1 L2 L3 L4 1`): primary `L2` (2 mH), secondary `L3` (500 uH, n=0.5),
and a 1:1 reset winding `L4` clamped by `D3` so the core flux resets during the off-time.
The secondary feeds a forward rectifier `D1`, freewheel diode `D2`, and an `L1`/`C1` output
filter into a 5 ohm load (`.tran 0 2m`, D=0.4 at 100 kHz).

This recipe was authored clean-room with qspice-mcp schematic tools and validated
end-to-end (netlist, simulation, `V(out)` check) with local QSpice.

## Preflight

1. `describe_server_capabilities` -- QSpice and simulation tools available.
2. `list_workflow_instructions` -- confirm `forward-converter-catalog` is listed.

## Source bundle

Recipe `forward_converter` ships inside qspice-mcp:

- `forward_converter.qsch` -- schematic (source of truth).
- `forward_converter.cir` -- validated netlist, ready to simulate.

## Steps

1. `materialize_reference_circuit(recipe_id="forward_converter")` -- both files in workspace root.
2. `run_simulation(source_path="forward_converter.cir")` -- runs the validated netlist.
3. `measure_waveform(signal="V(out)", operation="mean", t_start=1.6m, t_end=2m)`.

## Success criteria

- Transient completes with no convergence errors.
- Mean `V(out)` over the last 0.4 ms is 8.5-10.0 V (design value ~9.2 V).
- `V(sw)` peaks near `2*Vin` (96 V) during reset -- confirms the reset winding works.

## If blocked

| Symptom | Action |
| --- | --- |
| `V(out)` near 0 | Netlist is missing the `K1` coupling line; re-materialize or regenerate from the `.qsch` |
| Timestep-too-small error | Keep the bundled diode model (`Epsilon`/`Revepsilon` knee smoothing) |
| No `V(out)` | `list_signals`; the output net is named `out` |
| Need edits | Edit the materialized `.qsch` with schematic tools, then `generate_netlist` + `run_simulation` |

- Related topology block: `forward_converter` (see `describe_topology_block` for design equations).
