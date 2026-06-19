# Changelog

All notable changes to `qspice-mcp` are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0 releases may break the public API at any time).

## [Unreleased]

Initial public release — a Model Context Protocol server that lets AI assistants
drive the QSpice circuit simulator through stable JSON tools.

### Added

- **Default simulation timeout** — `QSPICE_TIMEOUT_S` (default 120s) in settings;
  applies when tools omit `timeout_s`; set to `0` to disable.
- **CLI `--version`** — `python -m qspice_mcp --version` prints the installed package version.
- **MCP Prompts (Phase 1)** — five bundled workflow prompts (`qspice_buck_converter_from_scratch`,
  `qspice_debug_convergence`, `qspice_run_and_measure`, `qspice_author_dll_device`,
  `qspice_sweep_design`).
- **`remove_wire` tool** — remove one wire segment by coordinates or pin selectors (mirrors `add_wire`).
- **`remove_net_label` / `remove_junction` tools** — schematic edit symmetry for labels and junctions.
- **`prepare_transient` tool** — stage a schematic or netlist with a documented `.tran` directive.
- **`prepare_ac` tool** — stage a schematic or netlist with a documented `.ac` directive.
- **`prepare_dc_sweep` tool** — stage a schematic or netlist with a documented `.dc` directive.
- **`prepare_loop_gain_analysis` tool** — stage `.ac` plus Tian/Middlebrook loop-gain guidance.
- **`set_component_position` tool** — move one placed schematic component to new coordinates.
- **`prepare_noise` / `prepare_transfer_function` / `prepare_sensitivity` / `prepare_temperature_sweep` tools** — analysis-prep helpers for remaining directive types.
- **MCP argument completions** — autocomplete for recipe IDs, instruction IDs, recipe documents, and workspace artifact paths.
- **`workspace-artifact://{relpath}` resource template** — sandbox-validated workspace artifact pull (`~` encodes `/` in nested paths).
- **MCP resource templates** — `recipe://{recipe_id}/manifest`, `/schematic`, and `/{document}` for pull-based recipe browsing.
- **`measure_step_response` tool** — rise time, delay, overshoot, and settling time from transient `.qraw` traces.
- **`measure_efficiency` tool** — average Pout/Pin from transient SAVEPOWERS-style power traces.
- **`read_fourier` tool** — parse native QSpice `.four` Fourier summaries from simulation logs.
- **`read_noise` tool** — parse integrated and spot `.noise` summary lines from simulation logs.

### Changed

- **Long-running MCP tools** — handlers flagged `ServiceSpec.long_running` now run on a
  worker thread (`anyio.to_thread`) so the async event loop stays responsive during sims/sweeps.
- **QSpice probe memoization** — `probe_qspice()` caches results per executable path + mtime
  (invalidates when the binary is replaced/upgraded).
- **Simulation cache key** — includes probed executable version and mtime so in-place QSpice
  upgrades cannot return stale cached artifacts.
- **Simulation artifact cache** — atomic staging + rename on `put()`, integrity hash verification on
  `get()`, and optional LRU eviction via `QSPICE_MAX_CACHE_BYTES`.
- **Child process lifecycle** — subprocess wrapper tracks PIDs; `atexit` + `SIGTERM`/`SIGINT` hooks
  terminate tracked QSpice/QUX children on shutdown.
- **MCP progress notifications (foundation)** — progress bridge bound per tool call; long-running tools
  report start/end progress; sequential and parallel sweeps report per-run progress.

- **Docs** — documented the public `write_workspace_text_file` auto-DLL contract:
  post-write `build_dll_device`, `dll_build` / `dll_build_error` degradation,
  optional `schematic_path` + `dll_reference` validation, existing-DLL skip, and
  MSVC-not-on-PATH behavior ([tool reference](docs/tool_reference.md),
  [user guide](docs/user-guide.md)).

- **Docs** — expanded MCP `connected=false` troubleshooting in the [user guide](docs/user-guide.md)
  and [AGENTS.md](AGENTS.md): absolute user-level paths, stale child processes,
  prefer `python -u -m qspice_mcp` over locked `.exe` launchers, editable-install
  drift after moving the repo, and `scripts/verify_mcp.ps1` / `verify_mcp_stdio.py`
  sanity checks.

- **Docs / MCP contracts** — standardized user-facing prose on the Qorvo-style
  product name **QSpice** across public markdown and MCP tool descriptions
  (including scaffold generator templates and returned notes). Code identifiers
  such as `QSPICE_EXE`, `QSPICE64.exe`, and install paths under
  `Program Files\QSPICE\` are unchanged. Corrected `SECURITY.md` to reference
  `QSPICE64.exe` instead of the nonexistent `QSPICE.exe`.

### Added

- **Agent skills catalog** — bundled client-side skills under
  `qspice_mcp/data/skills/` (`qspice-core`: `qspice-getting-started`,
  `qspice-convergence-debugging`), shipped as package data and installed into an
  agent's skills directory via `scripts/install_skills.ps1`. Skills are loaded by
  the agent (not the MCP server), adding no per-request server cost. Each skill's
  `manifest.yaml` `requires-tools` is validated against the live tool registry
  ([user guide](docs/user-guide.md)).

- **MCP server** — FastMCP stdio server (`qspice-mcp`) with runtime capability
  discovery (`describe_server_capabilities`), a stable error taxonomy
  ([docs/errors.md](docs/errors.md)), a `trace_id` on every response, and
  optional OpenTelemetry spans.
- **Schematic inspection and editing** — repo-owned clean-room `.qsch` editor
  with component, parameter, instruction, subcircuit, and embedded-symbol tools,
  plus preflight helpers (`describe_edit_capability`,
  `describe_schematic_edit_support`).
- **Schematic authoring** — build schematics from scratch (components, wires,
  junctions, net labels, `.DLL` blocks) plus bundled reference-circuit recipes
  and step-by-step workflow instructions.
- **Netlist and simulation** — run `.qsch`, `.cir`, or `.net` sources with
  transparent result caching; clean-room netlist generation with a companion
  `QUX.exe -Netlist` fallback for DLL/C-block schematics.
- **Sweeps and batches** — value, parameter, and model sweeps; background
  batches with resumable manifests and per-run recovery; remote-style session
  transport with artifact download.
- **Statistical analysis** — Monte Carlo and worst-case prepare/run/summarize
  with persisted plans and shared `.meas` aggregation.
- **Waveforms and results** — signal listing, budget-bounded waveform reads,
  scalar measurements, plots, operating-point inspection, log excerpts, and
  QPOST-backed measure extraction.
- **Exports** — QUX CSV/ASCII/SPICE/Touchstone exports, derived raw export and
  merge, and frequency-domain FFT/THD/Bode helpers.
- **Mixed-signal devices** — scaffold generators for C++ DLL, Verilog, socket,
  Python, I2C, and SPI custom devices; `build_dll_device` compiles C/C++ sources
  with the QSpice-bundled Digital Mars C++ toolchain, MSVC, or CMake.
- **Live GUI (Windows, optional)** — open or refresh schematics in the QSpice
  GUI and drive a version-gated external bridge for live cross-probing.
- **Safety** — workspace-sandboxed paths, validated CLI switches, and
  transactional artifact writes (see [docs/security.md](docs/security.md)).
- **Packaging** — base install runs without optional backends; `[backends]`,
  `[telemetry]`, and `[dev]` extras are opt-in; ships a `py.typed` marker for
  downstream type checkers.
