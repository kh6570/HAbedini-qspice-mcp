---
name: qspice-getting-started
description: Drive the QSpice MCP server end to end — discover or author a circuit, generate a netlist, run a simulation, and read or measure waveforms. Use when starting any QSpice task, when unsure which tool to call, when asked to simulate a circuit, build a buck/boost or other topology, inspect a .qsch, or read simulation results.
license: MIT
metadata:
  author: qspice-mcp
  version: "1.0"
---

# QSpice: Getting Started

How to drive the QSpice MCP server productively. QSpice is a circuit simulator;
this server exposes schematic authoring, simulation, and waveform analysis as MCP
tools. Read this first when you pick up any QSpice task.

## Core mental model

- **`.qsch` is the source of truth.** Netlists (`.net`/`.cir`), logs (`.log`), and
  waveforms (`.qraw`) are *derived* — regenerate them from the schematic rather
  than editing them by hand.
- **Bounded results.** `read_waveform` is capped (≈2000 points). Prefer
  `measure_waveform` for scalars (peak, RMS, settling) over dumping raw samples.
- **Sandbox.** All paths resolve against the server's workspace root. Use relative
  paths or pass `workspace_root` per call.
- **Degraded gracefully.** Optional backends (waveform reader, schematic editor,
  QUX exporter, DLL toolchain) may be missing. Call
  `describe_server_capabilities` first when anything fails unexpectedly — it
  reports which tool groups are healthy, partial, or degraded and why.

## First step: check the environment

Before non-trivial work, call **`describe_server_capabilities`**. It tells you:
whether QSpice is configured, which optional backends are available, which tool
groups are degraded, and feature flags. This avoids guessing when a later tool
returns a backend error.

## Two ways to get a circuit

### Track B — start from a bundled reference recipe (preferred when one fits)

1. `list_reference_circuit_recipes` — see available canonical circuits (id + title).
2. `describe_reference_circuit_recipe` — read one recipe's manifest, file list, and
   topology digest to confirm it matches the goal.
3. `materialize_reference_circuit` — copy the recipe's `.qsch` (+ sidecars like a
   C++ DLL source) into the workspace.
4. Optional: `list_workflow_instructions` → `read_workflow_instruction` for a
   step-by-step build/run prompt tied to that recipe.

### Track A — author from scratch (when no recipe fits)

1. `describe_topology_authoring_support` — check what scratch authoring supports.
2. `create_starter_schematic` (runnable source+load in one call) or
   `create_schematic` (blank) to begin.
3. Build topology: `add_component` (`R/C/D/V/L/B/nmos/pmos` or `GND`; use
   `auto_place=true` or `suggest_component_placement` for readable grids),
   `add_wire`, `add_junction`, `add_net_label`; adjust with `set_component_value`,
   `set_component_parameters`, `set_component_rotation`.
4. For custom devices, `write_workspace_text_file` writes a `.c`/`.cpp` source and
   auto-builds the sibling `.dll` (see the mixed-signal/DLL skills).

Install the **`qspice-schematic-layout`** skill when authoring scratch topology
so placement stays collision-free and upright.

## Inspect what you have

- `inspect_schematic` — summary of a `.qsch` and the analyses it defines.
- `list_components`, `list_subcircuits`, `read_component` — enumerate and drill in.
- `describe_edit_capability` — preflight: map an edit intent to the right tool with
  a go/no-go answer before mutating.

## Simulate

1. `generate_netlist` — resolve/stage the derived netlist (refreshes a stale
   sibling `.net` when the schematic is newer). Often optional —
   `run_simulation` can take a `.qsch` directly.
2. `run_simulation` — execute from a `.qsch`, `.cir`, or `.net`. This is
   long-running; expect a wait for transient analyses.

For design exploration use the sweep tools instead of repeated single runs:
`run_value_sweep`, `run_param_sweep`, `run_model_sweep`, `run_monte_carlo`,
`run_worst_case`. (These currently require a `.qsch` source.)

## Read results

- `read_log` — concise diagnostic excerpt + optional measures. **Always read the
  log after a run** to confirm it converged and completed.
- `list_signals` — enumerate signals in the `.qraw`.
- `measure_waveform` — scalar measurements (preferred).
- `read_waveform` — bounded samples when you need the actual trace.
- `plot_waveforms` — generate a plot artifact for selected signals.

## The canonical loop

```
describe_server_capabilities        # once, when unsure of environment
list/describe/materialize recipe    # or author from scratch (Track A)
inspect_schematic                   # confirm structure
run_simulation                      # execute
read_log                            # verify convergence/completion
list_signals → measure_waveform     # extract the answer
```

## When something fails

- Backend error → `describe_server_capabilities`, check the relevant group's state.
- Simulation didn't converge or stopped early → load the
  **qspice-convergence-debugging** skill.
- Missing `QSPICE_EXE` / `connected=false` → this is a setup/config issue, not a
  circuit issue; point the user to the server setup docs.

## Conventions

- Treat `.qsch` as source; never hand-edit derived `.net`/`.qraw`.
- Prefer `measure_waveform` over `read_waveform`; respect the sample budget.
- Read the log after every run before reporting results.
- Call `describe_server_capabilities` before assuming a tool is broken.
