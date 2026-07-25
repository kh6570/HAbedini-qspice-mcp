# Changelog

All notable changes to `qspice-mcp` are recorded in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(pre-1.0 releases may break the public API at any time).

## [Unreleased]

Initial public release — a Model Context Protocol server that lets AI assistants
drive the QSpice circuit simulator through stable JSON tools.

### Added

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
- **Agent skills catalog** — bundled client-side skills under
  `qspice_mcp/data/skills/` (`qspice-core`: `qspice-getting-started`,
  `qspice-convergence-debugging`), shipped as package data and installed into an
  agent's skills directory via `scripts/install_skills.ps1`. Skills are loaded by
  the agent (not the MCP server), adding no per-request server cost. Each skill's
  `manifest.yaml` `requires-tools` is validated against the live tool registry
  ([user guide](docs/user-guide.md)).
- **Three clean-room isolated converter recipes** — `forward_converter`,
  `half_bridge_converter`, and `full_bridge_converter` under
  `data/recipes/isolated_dc_dc/`, authored from the topology-pack blueprints with
  this server's own schematic tools (components, pin-anchored wires, coupled-inductor
  transformers via `K` statements, staged `.tran`) and validated end-to-end with local
  QSpice (`materialize` → `run_simulation` → `V(out)` inside the design band). Each
  ships the `.qsch` source of truth plus the validated `.cir` netlist and links to its
  matching topology block.
- **`qspice_tolerance_analysis` MCP prompt** — Monte Carlo plus worst-case tolerance
  workflow: `prepare_monte_carlo` → `run_monte_carlo`, `prepare_worst_case` →
  `run_worst_case`, then `summarize_tolerance_analysis` for a compact yield/extreme
  report.
- **`describe_server_capabilities` `guidance` block** — advertises available MCP
  prompt names, static and template resource URIs, and the bundled skills install
  pointer so agents can discover guidance surfaces at runtime.
- **Output budget parameters** — `inspect_schematic(max_components=…)`,
  `list_signals(name_filter=…, limit=…)`, `read_log`/`read_measures(max_measure_rows=…)`,
  and `read_workflow_instruction(max_chars=…)` bound large responses; each reports a
  matching `*_truncated` flag. Defaults preserve prior behavior.
- **Recipe `topology_block` + `tags` surfaced** — `list_reference_circuit_recipes`
  rows and `describe_reference_circuit_recipe` now expose each recipe's topology-pack
  link (plus an optional `topology_block_note`) and discovery tags; all bundled
  manifests declare `tags`.
- **`create_dll_device_from_spec` tool** — creates one `.DLL` custom device from a
  PinDef-style pin specification in a single call: place the block with all pins
  (inline `device_name` + `pins` array, or a workspace JSON spec file with
  `{schema_version: 1, device_name, description?, pins: [{name, direction}]}`), then
  optionally scaffold the contract-matched C++ source. Replaces the
  one-call-per-pin `add_dll_block_pin` loop for multi-pin devices such as
  microcontrollers, so an agent can go datasheet → pin spec → placed block +
  source in one step.
- **`.qsym` symbol interop** — two new tools round-trip symbols between embedded
  `.qsch` form and standalone `.qsym` symbol files (same guillemet wire format):
  `export_symbol_to_qsym` writes one component's embedded symbol as a standalone
  `.qsym`, and `add_component_from_qsym` places a `.qsym` symbol into a schematic
  with a new reference designator. Enables consuming and producing external
  QSpice symbol libraries (for example device symbols generated by PinDef-style
  toolchains).
- **`describe_device_spec` tool** — returns the v1 PinDef-style device-spec JSON
  schema, accepted pin directions, and a bundled ATtiny-style example
  (`attiny85.v1.json`), mirroring `describe_schematic_layout_spec` so agents can
  discover the `create_dll_device_from_spec` input format at runtime.
- **Six new directive-staging tools** — `prepare_save` (`.save` trace limiting for
  large SMPS transients), `prepare_options` (allowlisted `.options` covering
  convergence — `cshunt`, `gmin`, `method`, … — Bode/FRA — `boderef`,
  `bodeampfreq`, … — and output bookkeeping — `savepowers`, `keepopinfo`),
  `prepare_meas` (template-based `.meas` staging with `find_at`/`avg`/`trig_targ`/
  `fra`/`four` kinds plus a validated `raw` escape hatch; `.meas fra` is the primary
  SMPS Bode verification hook), `prepare_net` (`.net` S/Y/Z/H network-parameter
  extraction alongside `.ac`), `prepare_four` (`.four` THD staging consumed by
  `read_fourier`), and `prepare_op` (`.op` bias-point staging). All follow the
  existing schematic-copy / netlist-append staging pattern.
- **`qspice_smps_loop_gain` MCP prompt** — end-to-end closed-loop SMPS workflow:
  settle with `.tran`, extract with `.bode`, measure margins, then verify the
  crossover independently with `.meas fra`.
- **`reference://directives` MCP resource** — bundled clean-room cheatsheet
  (`qspice-directives.md`) indexing QSpice analysis directives, `.meas` templates,
  and high-value `.options`, retrievable by agents at runtime.

- **Topology-foldered reference recipes (9 new)** — the bundled recipe catalog now
  groups recipes by topology under `data/recipes/<topology>/<recipe_id>/` (a new
  optional `directory` field in the recipe index; existing flat recipes are
  unchanged). Nine converters adapted from Prof. J. Marcos Alonso's public
  repositories (used with permission) ship validated (each simulates cleanly under
  QSpice): `flyback_qr`, `buck_boost_dcm`, `two_phase_buck`, `llc_resonant`,
  `series_resonant_src`, `parallel_resonant_prc`, `class_e`, `half_bridge_zvs`,
  and `npc_inverter`. Each bundles the original `.qsch` plus a self-contained `.cir`
  (Alonso's behavioral component library inlined) and records provenance in its
  `recipe.json` `source` block; see `data/recipes/NOTICE.md`. Discover them via
  `list_reference_circuit_recipes`; the recipe tool surface stays fixed (recipes are
  data, not tools).
- **Five more Alonso-adapted recipes (backlog batch)** — `push_pull_resonant`
  (`resonant_dc_dc/`, current-fed push-pull resonant; ships the QUX `.cir` with one added
  `.options cshunt=1e-12` for convergence) plus four C-block control recipes under a new
  `control_technique/` folder: `digital_pwm_cblock`, `digital_buck_closed_loop`,
  `digital_current_mode_buck`, and `pv_mppt_po`. The C-block recipes bundle the original
  `.qsch`, Alonso's C-block `.cpp` (build with `build_dll_device`; the source filename is
  preserved so the DLL matches the device name), and a self-contained QUX `.cir`. All five
  validated end to end (build → simulate → clean `.qraw`); each records provenance in its
  `recipe.json` `source` block.
- **Two more Alonso-adapted recipes (backlog closeout; 16 total)** — `voltage_fed_push_pull`
  (`inverter/`, voltage-fed push-pull resonant inverter, ~68 V-RMS sinusoidal output;
  ships the QUX `.cir`, converges with no extra options) and `push_pull_uc1846`
  (`isolated_dc_dc/`, UC1846 current-mode push-pull open loop, V(out)≈5 V). The UC1846
  recipe ships Alonso's corrected "- new" schematic revision (converges cleanly where the
  earlier revision failed the bias point) and bundles his behavioral `UC1846.sub` model
  (referenced by the netlist). Both validated end to end. This closes the Alonso recipe
  backlog; the PE-65 / PE-69 candidates were declined (converters duplicate the shipped
  digital buck recipes; their unique material is frequency-domain loop-gain/FRA analysis,
  outside the time-domain converter catalog).
- **Recipe source attribution surfaced by `describe_reference_circuit_recipe`** — the
  tool now returns a `source` block (author, repo, path, commit, permission, video,
  note) for recipes adapted from an external author, so J. Marcos Alonso is credited
  in the tool output itself; clean-room recipes return `source: null`.

### Changed

- **`scaffold_dll_device_from_symbol` per-instance state** — the generated C++
  scaffold now includes the QSpice per-instance state idiom: a `struct s<Device>`
  allocated lazily through the `**opaque` entry-point parameter (zero-initialized
  on first call per schematic instance) plus a `Destroy` export freed once per
  instance at simulation end. Stateful devices (counters, registers, MCU bridges)
  get a correct starting point instead of a bare TODO body; the symbol-contract
  pin bindings and export signature are unchanged.
- **Clean-room editor value lookup** — `get_component_value`/`set_component_value`
  and `get_component_parameters` now treat only the first reference-shaped symbol
  text as the refdes, so device names that themselves look like references (for
  example `ATTINY85`) are correctly read and updated as component values.
- **Clean-room `.qsch`/`.qsym` parser fidelity** — two-word metadata tag names
  (`library file:`, `shorted pins:`) keep their identity after a save/reopen
  round trip instead of splitting into a mangled tag, and pipe-delimited inline
  library payloads (`«library file: |.subckt ...|»`) are preserved verbatim,
  including embedded spacing. Fixes `library_file`/`shorted_pins` metadata
  reads on reopened schematics and imported `.qsym` symbols.
- **`prepare_bode_analysis`** — new optional `reference_node` (stages a companion
  `.options boderef=<node>` line for feedback references not at AC ground) and
  amplitude-shaping parameters `bode_amplitude_frequency`, `bode_low_power`,
  `bode_high_power` (`BODEAMPFREQ`/`BODELOPOW`/`BODEHIPOW`); results now include
  `companion_instruction`.
- **`prepare_dc_sweep`** — supports `sweep_mode` `lin`/`oct`/`dec`/`list` (with
  `list_values`) and an optional second sweep dimension (`second_source`, …) for
  transistor curve tracing; the previous linear one-dimensional call signature is
  unchanged.
- **`prepare_ac` / `prepare_noise`** — new `list` sweep type with an explicit
  `frequencies` array; `dec`/`oct`/`lin` behavior is unchanged.
- **Skills enriched from the QSpice help reference** — convergence-debugging skill
  gains a QSpice-specific `.options` table (`cshunt`, `gshunt`, `gminsteps`,
  `srcsteps`, `noopiter`, `feather`, `itl1`/`itl4`, `maxstep`, `ric`) and trap-ringing
  guidance; power-electronics skill gains the closed-loop `.bode` workflow
  (injection point, settling, `boderef`, amplitude shaping) and `.meas fra`
  verification path.
- **Legacy C++ DLL recipes relocated into topology folders** — `buck_converter_cpp`
  and `boost_converter_cpp` now live under `data/recipes/non_isolated_dc_dc/`, and
  `flyback_converter_cpp` under `data/recipes/isolated_dc_dc/`, for consistency with
  the topology-foldered catalog. Their `recipe_id`s (the stable public API identifiers)
  are unchanged, so `materialize_reference_circuit`/`describe_reference_circuit_recipe`
  calls are unaffected.
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
- **`full_bridge_converter` and `push_pull_converter` topology blocks (isolated,
  buck-derived)** — fourth and fifth `isolated_dc_dc` blocks, from Alonso Ch.7. Both
  give the CCM ratio `n*D` (lossy `n*D/(1 + r_L/R)`), the doubled-frequency ripple
  `dVout = dI_L/(16*C*fsw)` and boundary `R_lim = 4*L*fsw/(1-D)`, the DCM ratio
  `2*n/(1 + sqrt(1 + 4k/D**2))` with `k = 4*L*fsw/R`, and a CCM small-signal set
  identical to the forward (`Gd = n*Vin*(...)/Den`, `Gb = n*D*(...)/Den`, `Zo` identical,
  `Zi` the buck value over `n**2*D**2`) — with **no right-half-plane zero** and a
  **self-resetting core**. The two share every equation and differ only in switch
  voltage stress and structure: the full-bridge uses four H-bridge switches each blocking
  `Vin`, while the push-pull uses two ground-referenced switches on a center-tapped
  primary, each blocking `2*Vin` (and is flux-imbalance-prone, so current-mode control is
  preferred). Includes flux-balance, leakage, and isolated-feedback notes plus
  averaged-model fast-simulation tips. Verified against and cited to J. Marcos Alonso,
  *Modelling, Control and Simulation of DC-DC Converters* Ch.7 (clean-room restatement;
  no source files copied).
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
  `normalize_text=false`. The former `set_component_rotation` and
  `move_component_preserving_connections` aliases are removed (see Removed).
  `describe_edit_capability` gains a `move_component` intent and both
  `move_component`/`rotate_component` now point at `set_component_position`.
  *(Default-on connection-preservation and text normalization change the output of
  existing `set_component_position` callers — acceptable pre-1.0, called out here.)*
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
- **Leaner `tools/list` payload** — the per-call `workspace_root` override property is
  now advertised only on tools that take path-like arguments (every tool still accepts
  it at call time), its description is shortened, and every tool schema declares a
  `required` array. High-traffic tools (`add_component`, `run_simulation`,
  `read_waveform`, the `prepare_*` staging family, the DLL authoring trio, and more)
  gained per-property descriptions, and tool descriptions now cross-link alternatives
  (device-spec vs from-symbol vs blank DLL scaffolds; `add_instruction` points to the
  typed `prepare_*` tools).
- **Guidance surfaces refreshed** — all six bundled skills and their manifests now name
  the current tool surface (`prepare_*` staging family, device-spec DLL path, `.qsym`
  round-trip, measures tools); `qspice_author_dll_device` leads with
  `describe_device_spec` → `create_dll_device_from_spec`; `qspice_debug_convergence`
  names `run_simulation`/`prepare_options`; the `reference://directives` and
  measurement-guideline resources cover `prepare_options`, the measures tools, and
  `.meas fra`; `describe_server_capabilities` tool groups match the shipped registry.

### Removed

- **Deprecated placement alias tools** — `set_component_rotation` and
  `move_component_preserving_connections` are removed (breaking). Use
  `set_component_position`, which moves and/or rotates in one call, preserves
  attached connections by default, and normalizes refdes/value text.
- **Unregistered boost scratch document** — deleted the wrong-content
  `boost_converter_cpp/scratch.md` (a stale buck copy that no workflow referenced);
  the boost `catalog.md` was upgraded to the full Track-B structure instead.

### Fixed

- **`read_log` broken over MCP** — the service parameter was renamed `raw_path` →
  `log_path` (it takes a `.log` path, matching `list_measures`/`read_measures`), fixing
  a `Missing required tool argument` failure for every MCP `read_log` call; an
  MCP-handler-level regression test now covers the wiring.
- **Measure tools annotation honesty** — `read_log`, `list_measures`, and
  `read_measures` default `refresh_measures=true` can write a `.meas` sidecar via
  QPOST, so their ServiceSpecs no longer claim `read_only`.
- **Clean-room netlist keeps inductor coupling statements** — mutual-inductance
  schematic texts (e.g. `K1 L1 L2 1`), which QSpice netlists even though they do not
  start with a dot, previously vanished from clean-room generated netlists, silently
  breaking every transformer simulation. They are now emitted with the element lines.
- **`docs/errors.md` drift** — `configuration_invalid` is documented as `reserved`
  (matching `error_taxonomy.py`), and a unit test now asserts the errors table matches
  `ERROR_CODE_DEFINITIONS` so statuses cannot drift again.
- **`build_dll_device` MSVC vcvars quoting on Windows** — the `cl` bootstrap via
  `vcvars64.bat` now passes the script path as a discrete `cmd /c` argument instead of
  pre-quoting it inside a single command string. Pre-quoting caused Python's
  `list2cmdline` to backslash-escape the quotes (`\"...\"`), so `cmd.exe` could not find
  `vcvars64.bat` and every MSVC-only DLL build failed on machines without `cl` on PATH.

