In the name of God, the Most Gracious, the Most Merciful

# Convergence options

## Applying fixes via tools

- **Component value/parasitic:** `set_component_value` or `set_component_parameters` (for example add a series R, snubber C).
- **Add a part** (snubber, bleeder to GND): `add_component` + `add_wire` (+ `add_junction` / `add_net_label` as needed).
- **Simulator directives** (`.options reltol=...`, `.ic ...`, `.options gmin=...`): use `prepare_options` to stage a copy with the options line, or `add_instruction` on the `.qsch`. For netlists you can also `generate_netlist`, append the `.options`/`.ic` line, then `run_simulation` on that `.net`/`.cir`.

### Useful directive starting points

```spice
.options reltol=0.005        ; loosen from default 0.001 if borderline
.options gmin=1e-10          ; help DC operating point
.options method=gear         ; more stable integration for stiff circuits
.ic V(out)=0 V(sw)=0         ; seed a known operating point
```

Loosen tolerances only modestly — over-loosening trades accuracy for convergence.

### QSpice-specific convergence options

QSpice extends the classic option set (see the `.options` table in the QSpice help). The most useful for convergence work:

| Option | Effect | When to try |
| --- | --- | --- |
| `cshunt=1e-12` | Adds that capacitance from every node to ground (aka CMIN) | Ideal-switch / resonant tanks that abort with `timestep too small`. Proven fix for the bundled `push_pull_resonant` recipe (1 pF is negligible at 100 kHz) |
| `gshunt=1e-12` | Conductance from every node to ground | Floating or nearly-floating nodes that break the DC solve |
| `gminsteps=0` / `srcsteps=0` | Disable gmin or source stepping (adaptive step counts are otherwise automatic) | When a stepping algorithm itself loops or misleads |
| `noopiter` | Skip direct OP iteration, go straight to gmin stepping | Hard bias points where direct Newton iteration always fails |
| `feather=<x>` | Trap integration damping factor | Trap ringing without paying Gear's accuracy cost |
| `itl1=500` / `itl4=100` | Raise DC / transient iteration limits | `iteration limit` messages on legitimately hard circuits |
| `maxstep=<t>` | Cap the timestep for `.tran` and `.bode` | Missed switching edges, chatter around discontinuities |
| `max1ststep=<t>` | Cap only the very first timestep (default 100 ns) | First-step blowups right after the bias point |
| `ric=<r>` | Impedance of sources asserting `.ic` (default 1 mΩ) | `.ic` conditions fighting the circuit at t=0 |

Prefer physical fixes first; `cshunt`/`gshunt` are the gentlest global options because tiny values barely perturb the answer while removing infinitely fast nodes.

The full directive and `.options` cheatsheet is available at runtime as the `reference://directives` MCP resource.
