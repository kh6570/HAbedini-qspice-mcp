# Changelog

All notable changes to `qspice-mcp` are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0 releases may break the public API at any time).

## [Unreleased]

Initial public release — a Model Context Protocol server that lets AI assistants
drive the QSpice circuit simulator through stable JSON tools.

### Added

- **`ingest_topology_contribution`** — validates a candidate topology-block manifest
  plus its clean-room blueprint and stages them (`manifest.json`, blueprint,
  `index_entry.json`) into a sandboxed `topology_contributions/<block_id>/` folder
  under the workspace for PR review. Never mutates the bundled knowledge pack; writes
  are sandbox-validated.
- **`inspect_schematic` merged sections** — optional `include_parameters` (returns
  schematic-level `.param` directives) and `include_connectivity` (attaches the
  net-to-pin `read_net_connectivity` report, degrading to `null` for unsupported
  schematics) collapse the common inspect-then-read pattern into one call.
- **Live-GUI `run_netlist` reuse (server side)** — with `session_mode=auto` plus a
  configured bridge, `run_simulation` dispatches a documented `run_netlist` command to
  a running live-GUI session and reports `session_strategy="reuse_live_gui"`; any
  timeout, missing session, or bridge unavailability safely falls back to a cold launch
  (behavior unchanged when no bridge ships). See the user guide bridge-contract section.
- **Topology knowledge pack** — bundled clean-room converter blueprints
  (`list_topology_blocks`, `describe_topology_block`, `search_topology_blocks`,
  `validate_topology_contribution`) for buck, boost, and buck-boost stages, with
  parameterized design equations and control notes. Cites J. Marcos Alonso,
  *Modelling, Control and Simulation of DC-DC Converters* (ISBN 979-8278321743)
  as a theoretical reference; no third-party schematic/netlist/source files are
  copied or redistributed.
- **`flyback_converter` topology block (isolated)** — first `isolated_dc_dc` block in
  the knowledge pack, covering the coupled-inductor flyback: CCM ratio `n*D/(1-D)`,
  primary/secondary ripples, device-stress (switch `Vin + Vout/n`, diode `n*Vin + Vout`),
  the CCM-DCM boundary, the turns-ratio-independent DCM ratio `D/sqrt(2*L1*fsw/R)`, and
  the full CCM small-signal set (`Gd`/`Gb`/`Zo`/`Zi` plus the control-to-output
  right-half-plane zero) expressed as the buck-boost results with inductance `L2 = n**2*L1`.
  Includes leakage-spike/snubber and isolated-feedback notes plus an averaged-model
  fast-simulation tip. Verified against and cited to J. Marcos Alonso, *Modelling,
  Control and Simulation of DC-DC Converters* Ch.4 (clean-room restatement; no source
  files copied).
- **`forward_converter` topology block (isolated, buck-derived)** — second `isolated_dc_dc`
  block, covering the transformer-isolated forward converter with an LC output filter:
  CCM ratio `n*D` (lossy `n*D/(1 + r_L/R)`), the transformer-reset constraint
  `D_max < 1/(1 + n31)` with switch stress `(1 + 1/n31)*Vin`, inductor/output ripples, the
  CCM-DCM boundary, the DCM ratio `2*n/(1 + sqrt(1 + 4k/D**2))`, and the full CCM
  small-signal set (`Gd`/`Gb` are `n` times the buck, `Zo` is identical, `Zi` is the buck
  value over `n**2`) — with **no right-half-plane zero**, the key advantage over the
  flyback. Includes reset-method, leakage, and isolated-feedback notes plus an
  averaged-model fast-simulation tip. Verified against and cited to J. Marcos Alonso,
  *Modelling, Control and Simulation of DC-DC Converters* Ch.5 (clean-room restatement;
  no source files copied).
- **`half_bridge_converter` topology block (isolated, buck-derived)** — third
  `isolated_dc_dc` block, covering the two-switch half-bridge with an input-capacitor
  divider and full-wave secondary rectifier: CCM ratio `n*D/2` (lossy
  `(n*D/2)/(1 + r_L/R)`), the doubled-frequency ripple `dVout = dI_L/(16*C*fsw)` and
  boundary `R_lim = 4*L*fsw/(1-D)`, device stress (switch blocks the full bus `Vin`,
  rectifier `n*Vin/2`), the DCM ratio `n/(1 + sqrt(1 + 4k/D**2))` with `k = 4*L*fsw/R`,
  and the full CCM small-signal set (`Gd`/`Gb` are `n/2` times the buck, `Zo` is
  identical, `Zi` is the active input over `n**2*D**2` in parallel with the input-cap
  divider) — with **no right-half-plane zero** and a **self-resetting core** (no reset
  winding, no `D < 0.5` limit). Includes flux-balance, leakage, and isolated-feedback
  notes plus an averaged-model fast-simulation tip. Verified against and cited to
  J. Marcos Alonso, *Modelling, Control and Simulation of DC-DC Converters* Ch.6
  (clean-room restatement; no source files copied).
- **Scratch-authored buck e2e** — `tests/integration/test_scratch_buck_authoring.py`
  authors the full buck from an empty workspace via MCP tools only (shared
  `scratch_buck.blueprint.json`), builds the DLL, generates the netlist, runs the
  sim, and asserts `V(out) > 4V`; `scripts/verify_scratch_buck.py` drives the same
  blueprint manually.
- **Detached orphan watchdog** — Windows Job Object (kill-on-close) joins all
  simulator children so they are reaped even on a hard IDE kill, plus a
  cross-platform `--watchdog` CLI route (`--parent-pid` / `--child-pid`) as the
  fallback reaper.
- **Version-keyed log classification** — `classify_simulation_log` now resolves
  convergence/fatal regex rules by `probe.version` over a base rule set, ignores
  recoverable `Warning:` lines (fixes a singular-matrix false positive), and is
  pinned by a committed QSpice log corpus (`tests/data/qspice_logs/`).
- **`QSPICE_SESSION_MODE` / `--session-mode`** — `cold` (default) always
  cold-launches a fresh simulation; `auto` reuses an available live-GUI session
  first (pure resolver in `infra/session_mode.py`).
- **One-click `.mcpb` install bundle** — repo-root `manifest.json` (MCPB `uv`
  server type) plus `scripts/build_mcpb.ps1` produce a single-file bundle that
  prompts the host for the QSpice executable, workspace, and session mode on
  install (`docs/user-guide.md`).
- **MCP Roots workspace fallback** — when neither `--workspace-root` nor
  `QSPICE_WORKSPACE_ROOT` is set, the server now falls back to the MCP client's
  first advertised filesystem root (best-effort, cached, graceful when the client
  has no roots) before using the process default.
- **CLI↔env alias guard** — the documented `QSPICE_*` mirror for every launcher
  flag is enforced by a unit test (`tests/unit/test_cli_env_alias_mapping.py`),
  and `QSPICE_TRANSPORT` now takes effect when `--transport` is omitted.
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
- **`move_component_preserving_connections` tool** — move or rotate one component and follow attached wires, junctions, and net labels to the new pin coordinates.
- **`add_library_component` tool** — clone one component symbol from a template `.qsch` into a target schematic (generic library parts beyond the built-in kinds).
- **`render_schematic_image` tool** — render a supported `.qsch` (wires, junctions, components, labels) to a PNG preview.
- **`read_net_connectivity` tool** — report electrical nets and the component pins connected to each (read-only).
- **`check_schematic` / `check_netlist` tools** — read-only ERC-style checks (missing ground, floating/single-connection nets, duplicate refdes, missing values, conflicting labels) on `.qsch` and `.net`/`.cir` sources.
- **`compare_schematics` tool** — diff two supported `.qsch` files by components, field changes, and net counts.
- **`evaluate_waveform_expression` tool** — compute a derived trace from an arithmetic expression over existing signals (e.g. `V(out)-V(in)`, `V(n1)*I(L1)`).
- **`cancel_run` tool** — request cancellation of an in-flight `run_simulation` invocation by its `run_id`.
- **CLI `--setup`, `--log-folder`, `--recipe-path`** — bootstrap diagnostics, optional file-log folder (`QSPICE_LOG_FOLDER`), and private recipe catalog override (`QSPICE_RECIPE_PATH`).
- **Experimental SSE transport gate** — `--transport sse` is gated behind `QSPICE_ENABLE_SSE=true`.
- **Companion agent skills** — `qspice-waveform-analysis`, `qspice-mixed-signal-dll`, and `qspice-power-electronics` added to the bundled `qspice-core` skill group.
- **`prepare_noise` / `prepare_transfer_function` / `prepare_sensitivity` / `prepare_temperature_sweep` tools** — analysis-prep helpers for remaining directive types.
- **MCP argument completions** — autocomplete for recipe IDs, instruction IDs, recipe documents, and workspace artifact paths.
- **`workspace-artifact://{relpath}` resource template** — sandbox-validated workspace artifact pull (`~` encodes `/` in nested paths).
- **MCP resource templates** — `recipe://{recipe_id}/manifest`, `/schematic`, and `/{document}` for pull-based recipe browsing.
- **`measure_step_response` tool** — rise time, delay, overshoot, and settling time from transient `.qraw` traces.
- **`measure_efficiency` tool** — average Pout/Pin from transient SAVEPOWERS-style power traces.
- **`read_fourier` tool** — parse native QSpice `.four` Fourier summaries from simulation logs.
- **`read_noise` tool** — parse integrated and spot `.noise` summary lines from simulation logs.
- **`list_includes` / `resolve_model_libraries` tools** — discover and resolve netlist include/library dependencies.
- **`import_circuit_bundle` tool** — copy a workspace-local `.qsch` and sibling sidecars into a destination folder.
- **`add_library_include` / `add_model` tools** — append netlist include directives and SPICE model blocks to workspace library artifacts.
- **Recipe catalog discovery guidance** — `list_reference_circuit_recipes` and `describe_reference_circuit_recipe` return shared `discovery_guidance` text.
- **MCP client log mirroring** — tool lifecycle structlog events mirror to the MCP client when supported.
- **ServiceSpec-driven tool annotations** — `resolve_tool_annotations()` derives MCP hints from `ServiceSpec`; removed dead `@tool_def` registration path.
- **Full MCP client log mirroring** — structured structlog events mirror to the MCP client for info+ (debug for `mcp.tool` only).
- **Dedicated boost recipe bundle** — `boost_converter_cpp` manifest now references `Boost-converter.qsch` and `boost_controller.cpp`.
- **Second bundled recipe** — `boost_converter_cpp` catalog entry proving `data/recipes/{recipe_id}/` modularity.
- **Include-aware simulation cache** — cache keys now hash resolved `.include`/`.lib` file contents.
- **Simulation phase progress** — `run_simulation` polls the `.log` for percent-complete lines and mirrors them via MCP progress + `ctx.info` when supported.
- **Declarative MCP handler bindings** — `build_raw_tool_handlers()` auto-wires ~85% of tools from the service catalog; mixin classes no longer drive runtime dispatch.
- **ServiceSpec destructive/idempotent hints** — `destructive` and `idempotent` on `ServiceSpec` drive MCP annotation hints (default: read-only tools are idempotent).
- **Service-package MCP contracts** — `services/<group>/mcp_contracts.py` rows merge onto enriched `ServiceSpec` at catalog discovery; retired `mcp/_tool_metadata/`.
- **DLL build toolchain probe** — `describe_server_capabilities` reports `optional_backends.dll_build_toolchain` with bundled DMC, MSVC/vcvars, and CMake availability separate from simulator configuration.
- **Auto DLL build fallback** — `build_dll_device(toolchain='auto')` retries MSVC then CMake when bundled DMC compile fails.
- **`dll_build_hints` on write failures** — `write_workspace_text_file` auto-build errors include toolchain recovery suggestions from `describe_server_capabilities`.
- **`scripts/verify_scratch_buck.py`** — Track A scratch buck MCP smoke script (`--workspace-root`, `--with-dll-build`, `--with-sim`).
- **`suggest_component_placement` tool** — grid-based collision-free placement with default 0° rotation; `add_component` accepts `auto_place=true`.
- **`describe_schematic_layout_spec` / `apply_schematic_layout_spec` tools** — v1 JSON layout spec for batch component placement (`auto`, `grid`, `absolute` modes); bundled `scratch_power_stage.v1.json` example.
- **`normalize_component_text_rotation` tool** — reset refdes/value symbol text to upright readable orientation, compensating for component body rotation.
- **MCP handler optional-arg fix** — omitted/null tool params no longer override Python service defaults (`add_component`, `read_waveform`, `plot_waveforms`, etc.).
- **`inspect_schematic` schema fix** — MCP descriptor now exposes `schematic_path`; handler maps it to the service `raw_path` parameter.
- **`create_starter_schematic` net naming** — series V–R–GND starter labels `VIN` on the source side and uses separate GND symbols (no spanning GND bus).
- **`qspice-schematic-layout` skill** — bundled agent guidance for readable scratch placement.

### Changed

- **Buck, boost, and buck-boost topology blocks enriched with CCM/DCM and small-signal
  theory** — the bundled `buck_converter`, `boost_converter`, and `buck_boost_converter`
  manifests and blueprints now cover the lossy CCM conversion ratio (buck
  `D/(1+r_L/R_load)`; boost `1/((1-D)+r_L/((1-D)R_load))`; buck-boost
  `D/((1-D)+r_L/((1-D)R_load))` with their high-duty gain roll-off), the CCM-DCM boundary
  (`R_lim`, `Io_lim`), the DCM conversion ratio and ripple, and the CCM small-signal
  transfer functions (`Gd`, `Gb`, `Zo`, `Zi` sharing one characteristic polynomial —
  including the boost and buck-boost control-to-output right-half-plane zeros), plus
  `r_L`/`r_C`/`R_load` parameters and an averaged-model fast-simulation tip. The
  buck-boost adds its `Vin + |Vout|` device-stress note and `D**2`-scaled input impedance.
  Equations verified against and cited to J. Marcos Alonso, *Modelling, Control and
  Simulation of DC-DC Converters* (clean-room restatement; no source files copied).
- **Topology search is now lexical TF-IDF retrieval** — `search_topology_blocks` ranks
  blocks by cosine relevance over the full corpus (index fields + manifest detail +
  blueprint text) instead of index-only substring scoring, so blueprint-only terms now
  match. `score` is a float in `[0, 1]`; results add `matched_fields`, and an optional
  `limit` (default 10) caps the result set. Neural-embedding RAG (needs bundled model
  weights) remains deferred.
- **Robust per-version log classification** — `resolve_log_rules` now normalizes the
  probed version and matches override keys/aliases with a prefix rule, fixing a latent
  bug where Windows dotted-quad/CLI versions never matched the timestamp-style override
  key and silently fell back to the base rules. Added a clearly-labeled synthetic
  second-build corpus (`tests/data/qspice_logs/v2_20271231/`) proving cross-build
  divergence handling; `LOG_CLASSIFICATION_VERSION` bumped to 3. The committed log
  corpus is now tracked in git (previously gitignored).
- **Unified, safe-by-default placement edits** — `set_component_position` is now the
  single move/rotate tool: pass `position_x`/`position_y` and/or `rotation_degrees`
  (at least one). By default it preserves attached connections (wires, junctions, net
  labels follow the pins, `preserve_connections=true`) and resets refdes/value text to
  upright readability (`normalize_text=true`), reporting `rewired_endpoints` and
  `normalized_text_count`. Opt out with `preserve_connections=false` /
  `normalize_text=false`. `set_component_rotation` and
  `move_component_preserving_connections` are retained as **deprecated aliases** that
  delegate to this path (removal in a future breaking release). `describe_edit_capability`
  gains a `move_component` intent and both `move_component`/`rotate_component` now point
  at `set_component_position`. *(Default-on connection-preservation and text
  normalization change the output of existing `set_component_position`/
  `set_component_rotation` callers — acceptable pre-1.0, called out here.)*
- **Opt-in orphan cleanup on `remove_component`** — new `remove_orphan_wires` flag
  (default `false`) prunes wires touching a now-orphaned pin coordinate plus junctions
  and net labels sitting on one, reporting `wires_removed` / `junctions_removed` /
  `net_labels_removed`. Off by default because auto-deleting wires is hard to undo in
  an agent loop.
- **MCP runtime handler registration** — `QSpiceToolRuntime` builds handlers from the service catalog + `expose_tool_schema()` instead of a 13-class mixin MRO; legacy mixin modules remain as service-import shims for tests.
- **Long-running MCP tools** — handlers flagged `ServiceSpec.long_running` now run on a
  worker thread (`anyio.to_thread`) so the async event loop stays responsive during sims/sweeps.
- **QSpice probe memoization** — `probe_qspice()` caches results per executable path + mtime
  (invalidates when the binary is replaced/upgraded).
- **Simulation cache key** — includes probed executable version and mtime so in-place QSpice
  upgrades cannot return stale cached artifacts.
- Removed unused `QSPICE_INITIALIZE_QSPICE_ON_STARTUP` setting (was never read by the server).
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
