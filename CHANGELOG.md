# Changelog

All notable changes to `qspice-mcp` are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0 releases may break the public API at any time).

## [Unreleased]

Initial public release — a Model Context Protocol server that lets AI assistants
drive the QSpice circuit simulator through stable JSON tools.

### Changed

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
