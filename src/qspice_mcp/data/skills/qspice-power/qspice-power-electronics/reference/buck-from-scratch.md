In the name of God, the Most Gracious, the Most Merciful

# Buck converter from scratch

Build a buck converter in the QSpice workspace using MCP tools only. Use the Vin, Vout, and Iout values supplied with the prompt. Keep netlists derived; treat `.qsch` as the source of truth.

1. Call `describe_topology_authoring_support` and `describe_server_capabilities`.
2. Optionally `list_reference_circuit_recipes` then `describe_reference_circuit_recipe` for `buck_converter_cpp` before authoring.
3. `create_schematic` or use `materialize_reference_circuit` only if a recipe is chosen.
4. Author the power stage with `add_component`, `add_wire`, `add_junction`, `add_net_label`. Follow `qspice-schematic-layout` so parts do not stack.
5. `add_instruction` or `prepare_transient` for `.tran`, then `generate_netlist`.
6. `run_simulation(dry_run=True)` then `run_simulation` on the derived netlist.
7. `list_signals` and `read_waveform` / `measure_waveform` on `V(out)` and the switch node.
