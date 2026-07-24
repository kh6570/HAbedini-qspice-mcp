---
name: qspice-convergence-debugging
description: Diagnose and fix QSpice simulations that fail to converge, stop early, or produce no usable waveform. Use when a run errors, the log shows "no convergence", "timestep too small", singular-matrix, or gmin-stepping failures, or when V(out) is missing/flat after a simulation.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.0"
---

# QSpice: Convergence Debugging

A structured workflow for simulations that fail to converge, abort early, or
yield empty/flat results. Convergence failures are about the *numerics and the
circuit*, not the MCP server.

## When to use

- `run_simulation` returns an error or the result has no/short waveform.
- `read_log` shows: `no convergence`, `timestep too small`, `singular matrix`,
  `gmin stepping failed`, `iteration limit`, or analysis stopped before the
  requested stop time.
- A signal that should be active is flat or missing in `list_signals`.

## When NOT to use

- `connected=false` / missing `QSPICE_EXE` → setup/config problem, not numerics.
- Backend-unavailable errors → call `describe_server_capabilities` first.

## Workflow

1. **Read the evidence.** `read_log` — identify the exact failure phrase and the
   time/node where it stopped. Don't guess before reading the log.
2. **Localize.** `inspect_schematic` + `list_components` — find the stage near the
   failing node (switching node, feedback, high-impedance net, nonlinear device).
3. **Form one hypothesis** from the table below and change **one thing**.
4. **Re-run** `run_simulation`, then `read_log` again. Iterate; change one factor
   at a time so you know what helped.

## Common causes → fixes

| Log symptom | Likely cause | Fix |
| --- | --- | --- |
| `singular matrix`, floating node | No DC path to ground; dangling net | Add a path to GND (large `R` to ground), fix unconnected pins; verify with `list_components` |
| `timestep too small` | Stiff switching, ideal edges, no parasitics | Add small series R / snubber; soften driver edges; `.options cshunt=1e-12`; relax `reltol` slightly |
| `no convergence` at t=0 | Hard DC operating point | Add `.ic` initial conditions; enable gmin/source stepping; add soft-start to sources |
| Stops mid-transient | Discontinuity / ideal switch chatter | Add hysteresis or RC snubber across the switch; add device parasitics; cap `maxstep` |
| Nonlinear/behavioral (`B`) blowup | Aggressive expression, divide-by-zero | Clamp/limit the `B` expression; add series resistance |
| Trap ringing (numerical oscillation) | Trapezoidal integration on stiff circuit | `.options method=gear` or `.options feather=...` (trap damping factor) |

## Applying fixes via tools

- **Component value/parasitic:** `set_component_value` or
  `set_component_parameters` (e.g. add a series R, snubber C).
- **Add a part** (snubber, bleeder to GND): `add_component` + `add_wire`
  (+ `add_junction` / `add_net_label` as needed).
- **Simulator directives** (`.options reltol=...`, `.ic ...`, `.options gmin=...`):
  use `prepare_options` to stage a copy with the options line, or `add_instruction`
  on the `.qsch`. For netlists you can also `generate_netlist`, append the
  `.options`/`.ic` line, then `run_simulation` on that `.net`/`.cir`.

### Useful directive starting points

```spice
.options reltol=0.005        ; loosen from default 0.001 if borderline
.options gmin=1e-10          ; help DC operating point
.options method=gear         ; more stable integration for stiff circuits
.ic V(out)=0 V(sw)=0         ; seed a known operating point
```

Loosen tolerances only modestly — over-loosening trades accuracy for convergence.

### QSpice-specific convergence options

QSpice extends the classic option set (see the `.options` table in the QSpice
help). The most useful for convergence work:

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

Prefer physical fixes first; `cshunt`/`gshunt` are the gentlest global options
because tiny values barely perturb the answer while removing infinitely fast
nodes.

## Verify the fix

After it runs to completion: `read_log` (clean exit, reached stop time) →
`list_signals` → `measure_waveform` on the target node to confirm the result is
physically sane (e.g. a buck `V(out)` near its expected regulation point), not
just "it ran."

## Conventions

- Read the log before changing anything; change one factor per iteration.
- Prefer adding real parasitics (series R, snubbers) over brute-force tolerance
  loosening — it's both more convergent and more physical.
- Re-confirm correctness with `measure_waveform`, not just a non-error exit.
