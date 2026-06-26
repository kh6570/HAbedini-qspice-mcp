# Tool Reference

This document describes the current public MCP tool surface for `qspice-mcp`.
Every tool listed below is implemented and registered by the server; call
`describe_server_capabilities` at runtime to see which optional backends and
tool groups are active on a given machine.

## Current Status

- `qspice-mcp --describe` prints bootstrap JSON; `qspice-mcp` runs the FastMCP stdio server.
- Base install is MCP-usable without optional backends; `[backends]` enables richer schematic/raw paths.
- Every tool response includes `trace_id`; `QSpiceError` failures expose stable `error_code` (see [errors.md](errors.md)).
- Runtime discovery: `describe_server_capabilities` reports backends, degraded groups, and feature flags.

For install, client setup, and workflows see the [User guide](user-guide.md). Statuses in the table below reflect the shipped tool surface.

## Tool Design Rules

- Prefer `.qsch` paths over direct `.net` editing wherever possible.
- Keep read-only inspection separate from mutating or execution-oriented tools.
- Return compact structured summaries before returning large artifacts.
- Enforce `DataBudget` limits on waveform-like outputs.
- Require all filesystem paths to stay within configured workspace roots.
- Treat `.net`, `.log`, `.qraw`, and plot files as derived artifacts.

## Tool Set

| Tool | Status | Purpose |
| --- | --- | --- |
| `describe_server_capabilities` | implemented | Report runtime environment state, optional backends, degraded tool groups, feature flags, and published error codes. |
| `refresh_schematic_in_gui` | implemented | Refresh one workspace-local `.qsch` GUI view on Windows by reopen-only mode or force-restart-and-reopen mode. |
| `open_schematic_in_gui` | implemented | Open one workspace-local `.qsch` through the local Windows OS file association as a convenience launcher. |
| `describe_live_gui_support` | implemented | Report whether the optional Windows-only live GUI layer is usable and what remains external. |
| `scaffold_live_gui_session` | implemented | Write a version-gated live GUI manifest for an external Windows-message bridge. |
| `launch_live_gui_session` | implemented | Launch one configured external-bridge live GUI session from a generated manifest. |
| `poll_live_gui_session` | implemented | Read live or terminal status for one launched live GUI bridge session. |
| `send_live_gui_session_command` | implemented | Queue one live GUI bridge command for Windows-message translation. |
| `poll_live_gui_session_events` | implemented | Read persisted live GUI bridge events for one launched session. |
| `close_live_gui_session` | implemented | Close one launched live GUI bridge session and optionally delete its manifest. |
| `submit_batch` | implemented | Submit a background value, parameter, or model sweep batch with optional retained-artifact policy control. |
| `get_batch_status` | implemented | Read live status for one submitted background sweep batch. |
| `collect_batch_results` | implemented | Return completed results for one submitted background sweep batch. |
| `cancel_batch` | implemented | Request cancellation for one submitted background sweep batch. |
| `submit_remote_simulation` | implemented | Submit one remote-style single-run session for background local execution. |
| `poll_remote_run` | implemented | Read live status for one submitted remote-style single-run session. |
| `download_remote_artifacts` | implemented | Package selected remote-style session artifacts into one zip bundle. |
| `close_remote_session` | implemented | Close one remote-style session and optionally delete its staged zip bundle. |
| `summarize_batch` | implemented | Summarize one persisted batch manifest and its derived artifacts. |
| `export_measures_csv` | implemented | Flatten measurement rows from a persisted batch manifest into CSV. |
| `compare_waveforms` | implemented | Compare one scalar waveform measurement across runs in a persisted batch. |
| `describe_qux_export_support` | implemented | Report whether the companion `QUX.exe` export surface is available. |
| `export_derived_raw` | implemented | Write one filtered waveform selection to a derived binary raw artifact, with optional stepped reconstruction. |
| `merge_waveforms` | implemented | Merge multiple filtered waveform selections into one derived binary raw artifact, with optional stepped reconstruction. |
| `export_waveform_csv` | implemented | Export one or more waveform expressions through the documented QUX CSV path. |
| `export_waveform_ascii` | implemented | Export one or more waveform expressions through the documented QUX ASCII path. |
| `export_waveform_spice` | implemented | Export one or more waveform expressions through the documented QUX SPICE path. |
| `export_touchstone_s2p` | implemented | Export one or more waveform expressions through the documented QUX Touchstone S2P path. |
| `generate_dll_variables` | implemented | Generate `.DLL` variable declarations through the documented QUX companion command. |
| `describe_mixed_signal_support` | implemented | Report which mixed-signal custom-device scaffold generators are available. |
| `validate_dll_symbol_signature` | implemented | Cross-check one `.DLL` schematic symbol against a C or C++ source file. |
| `build_dll_device` | implemented | Compile a workspace C or C++ source file into a `.dll` custom device using QSpice-bundled DMC, MSVC (`cl`), or CMake. |
| `scaffold_dll_device` | implemented | Generate a C++ DLL custom-device project scaffold with the documented QSpice entry points. See [C-Block Build Guide](cblock_build_guide.md) for compilation. |
| `scaffold_dll_device_from_symbol` | implemented | Generate a C++ DLL scaffold directly from one existing `.DLL` schematic block. See [C-Block Build Guide](cblock_build_guide.md) for compilation. |
| `scaffold_verilog_device` | implemented | Generate a Verilog module scaffold for QSpice Verilog device integration. |
| `scaffold_socket_device` | implemented | Generate a Python socket-server scaffold for QSpice socket-based device workflows. |
| `scaffold_python_device` | implemented | Generate a Python-backed custom-device server scaffold for QSpice Python device integration. |
| `describe_protocol_support` | implemented | Report which protocol co-simulation scaffold generators (I2C, SPI) are available. |
| `scaffold_i2c_device` | implemented | Generate a C++ DLL scaffold using QSpice's built-in I2C bus helper functions. |
| `scaffold_spi_device` | implemented | Generate a C++ DLL scaffold using QSpice's built-in SPI bus helper functions. |
| `materialize_reference_circuit` | implemented | Write server-bundled recipe artifacts into the workspace (for example `buck_converter_cpp`). |
| `import_circuit_bundle` | implemented | Copy a workspace-local `.qsch` schematic and sibling sidecars into a destination folder. |
| `list_reference_circuit_recipes` | implemented | List bundled reference-circuit recipe ids and short summaries (Track B discovery). |
| `describe_reference_circuit_recipe` | implemented | Return one bundled recipe manifest, workflow entries, file list, and topology digest. |
| `create_schematic` | implemented | Create a blank `.qsch` file so later schematic tools can build from scratch. |
| `create_starter_schematic` | implemented | Create a runnable source-load starter schematic in one call. |
| `add_component` | implemented | Insert one supported part (`R/C/D/V/L/B/nmos/pmos`) or a `GND` ground label; optional `auto_place` uses the layout grid. |
| `add_dll_block` | implemented | Insert one `.DLL` custom-device block with starter input and output pins into a schematic. |
| `add_dll_block_pin` | implemented | Insert one input or output pin into an existing `.DLL` block symbol. |
| `add_component_symbol_drawing` | implemented | Insert one embedded symbol drawing item from a raw tag name and argument list. |
| `add_wire` | implemented | Insert one wire segment into a schematic. |
| `remove_wire` | implemented | Remove one wire segment from a schematic. |
| `remove_net_label` | implemented | Remove one net label from a schematic. |
| `remove_junction` | implemented | Remove one junction node from a schematic. |
| `add_junction` | implemented | Insert one junction node into a schematic wire graph. |
| `add_net_label` | implemented | Insert one net label into a schematic. |
| `write_workspace_text_file` | implemented | Write a sandboxed UTF-8 text file; for `.c`/`.cpp`/`.cc`/`.cxx` sources, auto-invokes `build_dll_device` on the sibling `.dll` unless opted out (see detailed section). |
| `describe_topology_authoring_support` | implemented | Report scratch topology authoring capabilities (Track A readiness map). |
| `describe_schematic_layout_spec` | implemented | Return the v1 JSON layout-spec schema, placement modes, and bundled example. |
| `apply_schematic_layout_spec` | implemented | Batch-place schematic components from a workspace JSON layout specification. |
| `suggest_component_placement` | implemented | Suggest collision-free coordinates for the next component on a readable left-to-right grid (0° rotation). |
| `list_workflow_instructions` | implemented | List bundled workflow build instructions (for example buck-converter-cpp). |
| `read_workflow_instruction` | implemented | Read one bundled workflow instruction document with build steps and coordinate tables. |
| `inspect_schematic` | implemented | Summarize a `.qsch` file and the analyses it defines. |
| `read_net_connectivity` | implemented | Report electrical nets and the component pins attached to each for a supported `.qsch`. |
| `check_schematic` | implemented | Run read-only ERC-style checks on a supported `.qsch` (ground, floating pins, duplicate refdes, missing value, conflicting labels). |
| `check_netlist` | implemented | Run read-only ERC-style checks on a `.net`/`.cir` netlist (ground node 0, duplicate refdes, single-connection nodes). |
| `compare_schematics` | implemented | Diff two supported `.qsch` schematics by components and net counts. |
| `list_components` | implemented | Enumerate normalized component summaries from a `.qsch` file. |
| `list_subcircuits` | implemented | Enumerate subcircuit instances and indicate whether their definitions resolve. |
| `read_component` | implemented | Return a normalized view of one component, including nodes and parameters. |
| `read_component_symbol` | implemented | Return embedded symbol text, pin, drawing-item, drawing-tag, and image-asset metadata for one component. |
| `read_subcircuit` | implemented | Return a resolved view of one subcircuit instance or definition. |
| `save_schematic_as` | implemented | Write a `.qsch` file to a requested destination path. |
| `set_component_value` | implemented | Update the value field of one schematic component. |
| `set_component_rotation` | implemented | Rotate one placed component in 45-degree steps without moving it. |
| `set_component_position` | implemented | Move one placed component to new coordinates, optionally updating rotation. |
| `move_component_preserving_connections` | implemented | Move/rotate one component and follow attached wires, junctions, and net labels. |
| `add_library_component` | implemented | Clone one component symbol from a template `.qsch` into a target schematic. |
| `render_schematic_image` | implemented | Render a supported `.qsch` (wires, junctions, components, labels) to a PNG. |
| `set_component_parameters` | implemented | Update one or more component-local parameters. |
| `set_component_symbol_drawing` | implemented | Update one embedded symbol drawing item by replacing its raw tag name or arguments. |
| `set_component_symbol_text` | implemented | Update one embedded symbol text item, including safe layout/style attributes. |
| `normalize_component_text_rotation` | implemented | Reset refdes/value symbol text to upright readable orientation after symbol body rotation. |
| `set_component_symbol_pin` | implemented | Update one embedded symbol pin name, label geometry, or typed-pin metadata. |
| `set_dll_block_pin_role` | implemented | Move one `.DLL` block pin into the input or output role preset. |
| `remove_dll_block_pin` | implemented | Remove one pin from an existing `.DLL` block symbol. |
| `remove_component` | implemented | Remove one schematic component by reference and persist the edited schematic. |
| `remove_component_symbol_drawing` | implemented | Remove one embedded symbol drawing item by index. |
| `rename_component_reference` | implemented | Rename one schematic component reference, updating both the component object and its embedded symbol text. |
| `describe_edit_capability` | implemented | Preflight check: read a component, map an edit intent to the correct tool, return go/no-go with alternatives. |
| `describe_schematic_edit_support` | implemented | Return a static machine-readable capability map of every edit intent for AI go/no-go decisions. |
| `set_subcircuit_component_value` | implemented | Update one nested component value with explicit instance or definition scope. |
| `set_subcircuit_component_parameters` | implemented | Update nested component parameters with explicit instance or definition scope. |
| `set_element_model` | implemented | Update the model text of one schematic component. |
| `set_parameter` | implemented | Update a schematic-level `.param` directive. |
| `add_instruction` | implemented | Append one analysis instruction line using `instruction=`. |
| `remove_instruction` | implemented | Remove one exact or regex-matched directive from a schematic. |
| `generate_netlist` | implemented | Resolve or stage a derived netlist artifact for execution. |
| `list_includes` | implemented | List `.include`, `.inc`, and `.lib` directives reachable from one netlist. |
| `resolve_model_libraries` | implemented | Resolve `.lib` model-library paths referenced by one netlist. |
| `add_library_include` | implemented | Append one `.include`, `.inc`, or `.lib` directive to a netlist artifact. |
| `add_model` | implemented | Append one SPICE model definition block to a library or netlist file. |
| `save_netlist_copy` | implemented | Resolve or generate a derived netlist artifact at an explicit destination path. |
| `prepare_bode_analysis` | implemented | Stage a source with a documented `.bode` directive for closed-loop SMPS analysis. |
| `prepare_ac` | implemented | Stage a source with a documented `.ac` directive for small-signal frequency analysis. |
| `prepare_dc_sweep` | implemented | Stage a source with a documented `.dc` directive for DC sweep analysis. |
| `prepare_loop_gain_analysis` | implemented | Stage a source with `.ac` plus Tian or Middlebrook loop-gain guidance. |
| `prepare_noise` | implemented | Stage a source with a documented `.noise` directive. |
| `prepare_sensitivity` | implemented | Stage a source with a documented `.sens` directive. |
| `prepare_temperature_sweep` | implemented | Stage a source with a documented `.step temp` directive. |
| `prepare_transfer_function` | implemented | Stage a source with a documented `.tf` directive. |
| `prepare_transient` | implemented | Stage a source with a documented `.tran` directive for transient simulation. |
| `prepare_monte_carlo` | implemented | Persist explicit Monte Carlo parameter and component-value samples, with optional native `mc(...)` schematic staging and per-prefix component presets. |
| `prepare_worst_case` | implemented | Persist explicit worst-case corner assignments with shared component preset expansion. |
| `list_plot_suggestions` | implemented | Surface `.plot`, `.print`, `.probe`, and `.abscissa` hints from a source netlist. |
| `run_simulation` | implemented | Plan or execute a simulation from a `.qsch`, `.cir`, or `.net` source path. |
| `cancel_run` | implemented | Request cancellation of an in-flight `run_simulation` invocation by its `run_id`. |
| `run_value_sweep` | implemented | Run one schematic across multiple component values and optionally resume a matching retained batch with caller-selected retained-artifact policy. |
| `run_param_sweep` | implemented | Run one schematic across the Cartesian product of parameter values and optionally resume a matching retained batch with caller-selected retained-artifact policy. |
| `run_monte_carlo` | implemented | Execute one prepared Monte Carlo plan through the copy-on-write batch runner, with optional manifest-based resume and retained-artifact policy control. |
| `run_worst_case` | implemented | Execute one prepared worst-case plan through the copy-on-write batch runner, with optional manifest-based resume and retained-artifact policy control. |
| `run_model_sweep` | implemented | Run one schematic across multiple element models and optionally resume a matching retained batch with caller-selected retained-artifact policy. |
| `summarize_tolerance_analysis` | implemented | Aggregate Monte Carlo or worst-case target coverage and numeric `.meas` results. |
| `list_steps` | implemented | Enumerate available simulation steps and recovered `.step` variable assignments. |
| `list_signals` | implemented | Enumerate available signals from a `.qraw` file with lightweight metadata. |
| `read_device_operating_points` | implemented | Read device currents, powers, and node voltages from an Operating Point raw file. |
| `filter_device_operating_points` | implemented | Filter device operating-point entries by family, model, reference, or metric presence. |
| `summarize_device_operating_points` | implemented | Return compact family-level and extremum summaries for an Operating Point raw file. |
| `read_waveform` | implemented | Return bounded samples for one signal and selected component. |
| `evaluate_waveform_expression` | implemented | Evaluate an arithmetic expression over `.qraw` signals and return a budgeted series. |
| `measure_waveform` | implemented | Compute scalar measurements from one signal component. |
| `measure_bode_response` | implemented | Sample magnitude and phase from a frequency-domain waveform trace. |
| `measure_stability_margins` | implemented | Compute crossover frequency, phase margin, and gain margin from a loop-gain trace. |
| `measure_step_response` | implemented | Compute rise time, delay, overshoot, and settling time from a transient trace. |
| `measure_efficiency` | implemented | Compute average input/output power and Pout/Pin from transient power traces. |
| `compute_thd` | implemented | Estimate total harmonic distortion over a trailing integer-cycle waveform window. |
| `export_fft_spectrum` | implemented | Export a derived single-sided FFT spectrum as CSV. |
| `plot_waveforms` | implemented | Generate a derived plot artifact for selected signals. |
| `read_log` | implemented | Return a concise diagnostic excerpt and optional QPOST-derived measures. |
| `read_fourier` | implemented | Parse native `.four` Fourier summaries from a simulation log. |
| `read_noise` | implemented | Parse integrated and spot `.noise` summary lines from a simulation log. |
| `list_measures` | implemented | Enumerate QPOST-derived measurement blocks for one simulation log. |
| `read_measures` | implemented | Return structured measurement rows with optional measure and step filtering. |

The sections below describe the current contract for implemented tools and note
where optional or degraded modes still apply.

## describe_server_capabilities

Purpose:
Return a runtime capability snapshot for the active server environment,
including optional backend availability, degraded tool groups, selected adapter
details, telemetry readiness, feature flags, and the published stable error taxonomy.

Typical inputs:
- no tool-specific inputs beyond the current server runtime configuration

Expected outputs:
- `server`
- `telemetry`
- `qspice`
- `selected_adapter`
- `adapters`
- `optional_backends`
- `error_taxonomy`
- `feature_flags`
- `tool_groups`
- `degraded_groups`

Implementation dependencies:
- adapter probe and selection
- telemetry dependency and tracer-provider inspection through `infra/telemetry.py`
- optional backend detection for `RawRead`, `RawWrite`, and `QUX.exe`
- MCP server-definition feature reporting

## describe_live_gui_support

Purpose:
Describe the optional Windows-only live GUI layer, including whether the
current host can use it and which responsibilities remain outside the repo.

Typical inputs:
- no tool-specific inputs beyond the current server runtime configuration

Expected outputs:
- `windows_only`
- `platform_supported`
- `version_gated`
- `external_bridge_required`
- `session_manifest_scaffolding`
- `qspice_executable_configured`
- `runtime_session_management`
- `bridge_command_configured`
- `notes`

Notes:
This tool is intentionally honest about scope. The repo ships capability
reporting plus runtime lifecycle management for configured external bridges,
but it does not ship the bridge executable or claim richer live cross-probing
semantics than the configured bridge actually provides.

## open_schematic_in_gui

Purpose:
Open one workspace-local `.qsch` through the local Windows OS file association.

Typical inputs:
- `schematic_path`

Expected outputs:
- `schematic_path`
- `launcher`
- `started`
- `notes`

Notes:
This is a local-host convenience action, not a full live-GUI automation layer.
It is Windows-only, depends on the host file association for `.qsch`, and does
not guarantee refresh behavior for an already-open schematic window.

## refresh_schematic_in_gui

Purpose:
Refresh one workspace-local `.qsch` GUI view on Windows.

Typical inputs:
- `schematic_path`
- `strategy` (optional, one of `reopen_via_association`, `restart_qspice_and_reopen`)
- `force_restart` (optional, required when strategy is `restart_qspice_and_reopen`)

Expected outputs:
- `schematic_path`
- `strategy`
- `started`
- `qspice_process_restart_requested`
- `qspice_process_restart_exit_code`
- `notes`

Notes:
`reopen_via_association` keeps existing QSpice processes and dispatches another
OS association open request. `restart_qspice_and_reopen` can be more reliable
for stale-window refreshes because it force-restarts QSpice before reopen, but
it can close all open QSpice windows and therefore requires explicit
`force_restart=true`.

## scaffold_live_gui_session

Purpose:
Write a version-gated JSON manifest that an external Windows-message bridge can
use for optional live GUI orchestration and cross-probing.

Typical inputs:
- `session_name`
- `schematic_path` (optional)
- `waveform_names` (optional)
- `cross_probe_signals` (optional)
- `output_path` (optional)

Expected outputs:
- `session_name`
- `manifest_path`
- `schematic_path`
- `launch_command`
- `waveform_names`
- `cross_probe_signals`
- `notes`

Notes:
This tool writes a manifest contract with `transport = "windows_messages"`
plus `bridge_protocol.command_queue` and `bridge_protocol.event_log` channels,
but it does not execute QSpice or own live cross-probing itself. Empty session
names and empty list entries are rejected.

## launch_live_gui_session

Purpose:
Write or reuse a version-gated manifest and launch a configured external
Windows-message bridge process against it.

Typical inputs:
- `session_name`
- `schematic_path` (optional)
- `waveform_names` (optional)
- `cross_probe_signals` (optional)
- `output_path` (optional)

Expected outputs:
- `session_id`
- `session_name`
- `status`
- `manifest_path`
- `output_root`
- `bridge_command`
- `submitted_at`
- `bridge_pid`
- `notes`

Notes:
This tool requires a configured live GUI bridge command and a Windows host.
The repo launches the external bridge process, persists session state, and
provisions command/event files for bridge interaction, but the bridge
executable itself remains an external dependency.

## poll_live_gui_session

Purpose:
Read live or terminal status for one launched live GUI bridge session.

Typical inputs:
- `session_id`

Expected outputs:
- `session_id`
- `session_name`
- `status`
- `manifest_path`
- `output_root`
- `bridge_command`
- `submitted_at`
- `completed_at`
- `bridge_pid`
- `bridge_exit_code`
- `duration_s`
- `live_process_attached`
- `stdout_path`
- `stderr_path`
- `error`
- `notes`

## send_live_gui_session_command

Purpose:
Queue one command for the launched external live GUI bridge to translate into
Windows-message interaction.

Typical inputs:
- `session_id`
- `command`
- `signal` (optional)
- `payload` (optional object)

Expected outputs:
- `session_id`
- `command_id`
- `command`
- `signal`
- `payload`
- `queued_at`
- `command_path`
- `note`

Notes:
The manager appends one JSONL command record under the launched session's
output root. Terminal sessions reject new commands.

## poll_live_gui_session_events

Purpose:
Read bridge-produced live GUI events recorded for one launched session.

Typical inputs:
- `session_id`
- `after_sequence` (optional integer, default `0`)
- `limit` (optional integer, default `50`)

Expected outputs:
- `session_id`
- `status`
- `event_path`
- `next_sequence`
- `events`
- `live_process_attached`
- `notes`

Notes:
The bridge event log is read incrementally from the session's JSONL event
channel. Each event record currently carries a sequence number, event name,
optional signal name, payload object, and optional timestamp.

## close_live_gui_session

Purpose:
Terminate one launched live GUI bridge session and optionally delete its
generated manifest.

Typical inputs:
- `session_id`
- `delete_manifest` (optional boolean)

Expected outputs:
- `session_id`
- `status`
- `output_root`
- `manifest_path`
- `bridge_terminated`
- `manifest_deleted`
- `note`

## submit_batch

Purpose:
Submit a background value, parameter, or model sweep batch that executes runs
in a bounded parallel pool and persists a resumable manifest.

Typical inputs:
- `batch_kind` (one of `value`, `parameter`, `model`)
- `schematic_path`
- `values`, `parameters`, or `models` (depending on `batch_kind`)
- `output_dir` (optional)
- `resume` (optional boolean, re-attaches to a matching retained manifest)
- `retain_artifacts` (optional, one of `none`, `all`, `failed`)
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `extra_switches` (optional validated CLI switches)

Expected outputs:
- `batch_id`
- `status`
- `batch_kind`
- `schematic_path`
- `output_dir`
- `run_count`
- `resumed`
- `retain_artifacts`
- `dry_run`
- `manifest_path`

Notes:
Resumed batches re-validate manifest paths against the active workspace and
skip runs whose output artifacts already exist (unless `retain_artifacts` is
`none`, which deletes prior artifacts first). Failed or timed-out runs are
re-attempted on resume when their artifacts are missing or stale. Submitted
batch IDs now also persist a registry entry so later server instances in the
same workspace can reload completed status and terminal results by `batch_id`.
The `schematic_path` must be a `.qsch` source; `.net`/`.cir` inputs are
rejected because clean-room netlist editing for sweeps is not yet implemented.

## get_batch_status

Purpose:
Read live status for one submitted background sweep batch.

Typical inputs:
- `batch_id`

Expected outputs:
- `batch_id`
- `status`
- `run_count`
- `completed`
- `running`
- `pending`
- `failed`
- `dry_run`
- `manifest_path`
- `error` (present when the batch has terminated with an unrecoverable error)

Notes:
Status values are `pending`, `running`, `completed`, `failed`, and
`cancelled`. This is a lightweight poll; use `collect_batch_results` to
retrieve per-run detail. Later server instances can now rehydrate completed
and failed batches from persisted manifests. If a restart happens while the
batch was still non-terminal, the returned status is only the last persisted
snapshot because the current implementation does not yet take over an in-flight
worker pool.

## collect_batch_results

Purpose:
Return completed results for one submitted background sweep batch.

Typical inputs:
- `batch_id`

Expected outputs:
- `batch_id`
- `status`
- `run_count`
- `completed`
- `failed`
- `runs` (list of per-run metadata: index, label, exit_code, log_path, raw_path, error)

Notes:
Only returns results for runs that have finished (completed or failed).
Pending and running entries are not included. Call `get_batch_status` first
to confirm the batch is no longer `pending` or `running`. Completed or failed
batch IDs can now be collected after a later server restart as long as the
persisted manifest remains available inside the workspace.

## cancel_batch

Purpose:
Request cancellation for one submitted background sweep batch.

Typical inputs:
- `batch_id`

Expected outputs:
- `batch_id`
- `status`
- `cancelled_runs`
- `note`

Notes:
Cancellation is best-effort. Already-running QSpice processes are not
force-killed; the batch manager stops dispatching new runs and marks the
batch `cancelled`. Runs that were already in flight will complete normally.
After a server restart, restored non-terminal batch snapshots are readable but
not cancelable because no live manager thread remains attached to them.

## validate_dll_symbol_signature

Purpose:
Cross-check one `.DLL` schematic symbol against a C or C++ source file before
build or simulation.

Typical inputs:
- `schematic_path`
- `reference`
- `source_path`

Expected outputs:
- `schematic_path`
- `source_path`
- `reference`
- `device_name`
- `expected_export_name`
- `matched_export_name`
- `exported_function_names`
- `symbol_input_pin_names`
- `symbol_output_pin_names`
- `source_input_pin_names`
- `source_output_pin_names`
- `is_valid`
- `mismatches`
- `warnings`

Notes:
The current parser targets the real QSpice-style named exported-function flow
plus explicit `data[]` pin bindings with `// input` and `// output` comments,
which matches the checked-in Buck C++ example and the new symbol-driven DLL
scaffold.

## build_dll_device

Purpose:
Compile one workspace C or C++ custom-device source file into a `.dll` artifact
that QSpice can load beside the schematic.

Typical inputs:
- `source_path`
- `output_path` (optional; defaults to the source stem with `.dll`)
- `toolchain` (optional: `auto`, `dmc`, `msvc`, or `cmake`)
- `timeout_s` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `toolchain`
- `command`
- `exit_code`
- `duration_s`
- `stdout`
- `stderr`

Notes:
`auto` prefers QSpice-bundled DMC (`<QSPICE_EXE parent>/dm/bin/dmc.exe`) when
`QSPICE_EXE` resolves, then MSVC `cl` (including vcvars bootstrap), then CMake
when a `CMakeLists.txt` sits beside the source. `dmc` runs
`dmc -mn -WD <source> kernel32.lib` (32-bit, C++98-era limits). Compiler failures
return `validation_failed` with stderr context. All paths must stay inside the
configured workspace root.

## scaffold_dll_device_from_symbol

Purpose:
Generate a C++ DLL starter project directly from one existing `.DLL` schematic
block so the source stub matches the symbol contract already present in the
`.qsch` file.

Typical inputs:
- `schematic_path`
- `reference`
- `output_dir` (optional)

Expected outputs:
- `schematic_path`
- `reference`
- `device_name`
- `export_name`
- `input_pin_names`
- `output_pin_names`
- `source_path`
- `cmake_path`
- `source_line_count`
- `cmake_line_count`
- `notes`

Notes:
This tool is schematic-first by design. It reads the existing symbol pin order
and labels, emits matching `#undef` lines plus `data[]` pin bindings, and adds
an explicit note warning against shared global mutable state across multiple
DLL instances.

## scaffold_dll_device

Purpose:
Generate a C++ DLL custom-device project scaffold with the documented QSpice
entry points (`dll_device_count`, `dll_device`, `dll_device_end`).

Typical inputs:
- `device_name`
- `output_dir` (optional)
- `schematic_path` (optional)

Expected outputs:
- `device_name`
- `source_path`
- `cmake_path`
- `source_line_count`
- `cmake_line_count`
- `notes`

Notes:
When `schematic_path` is provided, the `.cpp` and `CMakeLists.txt` are placed
next to the schematic so QSpice's "Show Source" command finds them. Compile the
result with the [C-Block Build Guide](cblock_build_guide.md) or `build_dll_device`.
Use `scaffold_dll_device_from_symbol` instead when an existing `.DLL` block
already defines the pin contract.

## scaffold_verilog_device

Purpose:
Generate a Verilog module scaffold for the documented QSpice Verilog
device-integration path.

Typical inputs:
- `device_name`
- `output_path` (optional)

Expected outputs:
- `device_name`
- `output_path`
- `line_count`

Notes:
This emits a starter Verilog module only. Building and registering the device
with QSpice remains a manual external step.

## scaffold_socket_device

Purpose:
Generate a Python socket-server scaffold for the documented QSpice
socket-based custom-device workflow.

Typical inputs:
- `device_name`
- `output_path` (optional)

Expected outputs:
- `device_name`
- `output_path`
- `line_count`

Notes:
The scaffold is a starting point for an external co-simulation server. It does
not launch or supervise the socket process on the caller's behalf.

## scaffold_python_device

Purpose:
Generate a Python-backed custom-device server scaffold for the documented
QSpice Python device-integration path.

Typical inputs:
- `device_name`
- `output_path` (optional)

Expected outputs:
- `device_name`
- `output_path`
- `line_count`

Notes:
This emits a starter Python device server only; wiring it into QSpice remains a
manual external step.

## scaffold_i2c_device

Purpose:
Generate a C++ DLL scaffold that uses QSpice's built-in I2C bus helper
functions for protocol-level co-simulation.

Typical inputs:
- `device_name`
- `output_path` (optional)

Expected outputs:
- `device_name`
- `output_path`
- `line_count`

Notes:
The generated source calls the documented `qspice_i2c_*` helpers
(`qspice_i2c_read`, `qspice_i2c_write`, `qspice_i2c_start`, `qspice_i2c_stop`,
`qspice_i2c_ack`, `qspice_i2c_nack`). Compile it like any other C-block DLL.

## scaffold_spi_device

Purpose:
Generate a C++ DLL scaffold that uses QSpice's built-in SPI bus helper
functions for protocol-level co-simulation.

Typical inputs:
- `device_name`
- `output_path` (optional)

Expected outputs:
- `device_name`
- `output_path`
- `line_count`

Notes:
The generated source calls the documented `qspice_spi_read` and
`qspice_spi_write` helpers and defaults to a standard SPI mode. Compile it like
any other C-block DLL.

## describe_mixed_signal_support

Purpose:
Report which mixed-signal custom-device scaffold generators (`.DLL`, Verilog,
socket, Python) are available in the current runtime.

Typical inputs:
- none

Expected outputs:
- per-generator availability flags and short descriptions

Notes:
Read-only discovery tool. Call it before relying on a specific scaffold
generator so degraded or unavailable generators are detected up front.

## describe_protocol_support

Purpose:
Report which protocol co-simulation scaffold generators (I2C, SPI) are
available in the current runtime.

Typical inputs:
- none

Expected outputs:
- per-protocol availability flags and short descriptions

Notes:
Read-only discovery tool paired with `scaffold_i2c_device` and
`scaffold_spi_device`.

## add_junction

Purpose:
Insert one `junction (x,y)` node into a schematic wire graph.

Typical inputs:
- `schematic_path`
- `position_x`, `position_y`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `position_x`
- `position_y`

## write_workspace_text_file

Purpose:
Write one UTF-8 text file under the workspace root (for example a C-block `.cpp`).
For C/C++ custom-device sources (`.c`, `.cpp`, `.cc`, `.cxx`), the handler can
compile the sibling `.dll` in the same call via `build_dll_device`, and optionally
cross-check the DLL block symbol when `schematic_path` and `dll_reference` are both
set.

Typical inputs:
- `relative_path` — workspace-relative destination (required)
- `content` — UTF-8 file body (required)
- `overwrite` — allow replacing an existing file (default `false`)
- `build_dll_after_write` — when omitted, auto-build runs for `.c`/`.cpp`/`.cc`/`.cxx`
  sources; set `false` to write only
- `schematic_path` — optional `.qsch` for post-build symbol validation (requires
  `dll_reference`)
- `dll_reference` — DLL block reference such as `X1` (requires `schematic_path`)
- `dll_toolchain` — forwarded to `build_dll_device`: `auto` (default), `dmc`, `msvc`,
  or `cmake`
- `dll_timeout_s` — compiler timeout in seconds (default `120`)

Expected outputs (always):
- `output_path`
- `overwritten`
- `byte_count`
- `line_count`

Expected outputs (C/C++ auto-build path):
- `dll_build` — `build_dll_device` result object when compilation succeeds, or a
  degraded summary when rebuild was skipped (see Notes)
- `dll_build_error` — string message when compilation failed and no usable sibling
  `.dll` exists (the text file write still succeeded)
- `dll_validation` — `validate_dll_symbol_signature` result when both
  `schematic_path` and `dll_reference` were provided

Notes:
**Auto-build trigger.** After a successful write, auto-build runs when the file
suffix is one of `.c`, `.cpp`, `.cc`, or `.cxx` and `build_dll_after_write` is not
`false`. The output DLL path is always the source path with a `.dll` suffix in the
same directory.

**Toolchain selection (`dll_toolchain=auto`).** Matches `build_dll_device`: bundled
DMC beside `QSPICE_EXE` when configured, else MSVC (`cl` on PATH or via discovered
`vcvars64.bat`), else CMake when `CMakeLists.txt` sits beside the source. When
`QSPICE_EXE` is unset and `cl` is not on PATH (typical for IDE-spawned MCP without a
Developer Prompt), auto-build returns `dll_build_error` with a message such as
`No supported DLL build toolchain found…` rather than failing the write.

**Degraded success (`dll_build_error`).** A failed compile does not roll back the
written source file. The response includes `dll_build_error` and omits `dll_build`
when no sibling `.dll` exists. Callers can fix the source and retry, invoke
`build_dll_device` directly, or follow the [C-Block Build Guide](cblock_build_guide.md).

**Existing sibling `.dll`.** When `buck_controller.dll` already exists next to the
source, the server skips recompilation and returns `dll_build` with
`toolchain: "existing"` and `skipped_rebuild: true`. If compilation then fails but
the sibling DLL is still present, the same skipped summary is returned with an
optional `note` carrying the build error text.

**Optional symbol validation.** Pass both `schematic_path` and `dll_reference` to run
`validate_dll_symbol_signature` after the write/build step. The validation object is
always returned in `dll_validation`. When validation fails (`is_valid: false`), the
tool raises `ValidationError` — the source file (and any compiled DLL) remain on disk.

**MSVC not on PATH.** IDE-launched MCP often lacks `cl` even when Visual Studio is
installed. Set `QSPICE_EXE` so `auto` can use bundled DMC, pass `dll_toolchain="msvc"`
only from an environment where `cl` or `vcvars64.bat` is discoverable, or build
manually with `build_dll_device` / the cblock guide.

## describe_topology_authoring_support

Purpose:
Return the static Track A topology authoring capability map, including whether
scratch buck authoring is ready (`scratch_buck_ready`).

Typical inputs:
- none

Expected outputs:
- `capabilities` (capability, tool, supported, limitations)
- `scratch_buck_ready`
- `scratch_buck_instruction_id` (currently `buck-converter-cpp`)
- `notes`

## list_workflow_instructions

Purpose:
List bundled workflow instructions for scratch circuit authoring.

Typical inputs:
- none

Expected outputs:
- `instructions` (instruction_id, recipe_id, title, summary, track, document, related_instruction_id)

## read_workflow_instruction

Purpose:
Read one bundled workflow instruction (build steps, component/wire tables, C++ template).

Typical inputs:
- `instruction_id` (for example `buck-converter-cpp`)

Expected outputs:
- `instruction_id`
- `title`
- `summary`
- `track`
- `recipe_id`
- `related_instruction_id`
- `content` (markdown)

## list_reference_circuit_recipes

Purpose:
List bundled reference-circuit recipe ids, titles, and short summaries from
package data without writing files into the workspace.

Typical inputs:
- none

Expected outputs:
- `discovery_guidance` (shared catalog discovery workflow text)
- `recipes` (each with `recipe_id`, `title`, `summary`)

## describe_reference_circuit_recipe

Purpose:
Return one bundled reference-circuit manifest, workflow instruction rows,
bundled file list, and a lightweight topology digest parsed from the bundled
`.qsch` (component refs/kinds, analyses, `.param` directives).

Typical inputs:
- `recipe_id` (for example `buck_converter_cpp`)

Expected outputs:
- `recipe_id`
- `title`
- `description`
- `discovery_guidance` (shared catalog discovery workflow text)
- `files` (each with `relative_path`, `bundle_name`, `encoding`)
- `build_required`
- `build_hint`
- `workflows` (each with `instruction_id`, `title`, `summary`, `track`, `document`, `related_instruction_id`)
- `topology_digest` (when a schematic is bundled: `schematic_file`, `component_count`, `components`, `analyses`, `parameters`, `size_bytes`)

## materialize_reference_circuit

Purpose:
Write server-bundled reference circuit files into the workspace so an empty
folder can reproduce a canonical bundled recipe from package data.

Typical inputs:
- `recipe_id` (first recipe: `buck_converter_cpp`)
- `output_dir` (optional; defaults to the workspace root)
- `overwrite` (optional boolean)

Expected outputs:
- `recipe_id`
- `title`
- `description`
- `output_dir`
- `files` (each with `relative_path`, `output_path`, `overwritten`)
- `build_required`
- `build_hint`

Notes:
Bundled recipes ship inside the `qspice-mcp` package. The Buck C++ recipe
materializes `Buck-converter.qsch` and `buck_controller.cpp` as siblings;
follow with `build_dll_device` when `build_required` is true.

## import_circuit_bundle

Purpose:
Copy one workspace-local `.qsch` schematic and sibling sidecar files into a
destination folder.

Typical inputs:
- `schematic_path`
- `output_dir` (optional; defaults to the schematic's parent folder)
- `overwrite` (optional boolean)

Expected outputs:
- `source_schematic`
- `output_dir`
- `files` (each with `relative_path`, `output_path`, `overwritten`, `encoding`)

Notes:
Simulation artifacts such as `.net`, `.log`, and `.qraw` in the source folder
are skipped. Use this for importing user-authored bundles already present in the
workspace, distinct from `materialize_reference_circuit`.

## create_schematic

Purpose:
Create a blank `.qsch` file inside the workspace root so later tools can start
from an empty sheet.

Typical inputs:
- `output_path`
- `overwrite` (optional boolean)

Expected outputs:
- `output_path`
- `overwritten`

Notes:
This tool deliberately creates the smallest valid schematic artifact. It does
not place parts, wires, or directives by itself. It remains available from the
base install through a repo-owned clean-room writer; optional editor backends
are only needed for richer follow-on edits and inspections.

## create_starter_schematic

Purpose:
Create a runnable starter schematic with a voltage source, resistor load,
ground connection, labels, and one analysis instruction in a single call.

Typical inputs:
- `output_path`
- `overwrite` (optional boolean)
- `source_reference` (optional, defaults to `V1`)
- `source_value` (optional, defaults to `10`)
- `load_reference` (optional, defaults to `R1`)
- `load_value` (optional, defaults to `1k`)
- `input_net_name` (optional, defaults to `VIN`)
- `analysis_instruction` (optional, defaults to `.op`)

Expected outputs:
- `output_path`
- `overwritten`
- `source_reference`
- `source_value`
- `load_reference`
- `load_value`
- `input_net_name`
- `analysis_instruction`

Notes:
This tool remains available from the base install through a repo-owned
fixed-format clean-room writer when no optional schematic editor backend is
installed. It builds a series V–R–GND divider: label `VIN` on the
source-to-R node, separate GND symbols at V− and R pin 2 (no spanning GND
bus). For RC filters, place R then C manually or with
`apply_schematic_layout_spec`. The topology is designed to be immediately
runnable and to provide a concrete blank-start workflow the other schematic
tools can extend.

## add_component

Purpose:
Insert one supported simple part or ground label into a schematic and persist the edited
`.qsch` file.

Typical inputs:
- `schematic_path`
- `component_kind`
- `reference` (required for `resistor`, `capacitor`, `diode`, and `voltage_source`)
- `value` (required for `resistor`, `capacitor`, `diode`, and `voltage_source`)
- `position_x` (optional integer)
- `position_y` (optional integer)
- `rotation_degrees` (optional integer, multiple of 45)
- `auto_place` (optional boolean; use layout grid instead of explicit coordinates)
- `net_name` (optional; used for `ground`, defaults to `GND`)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `component_kind`
- `reference`
- `value`
- `position_x`
- `position_y`
- `rotation_degrees`
- `net_name`

Notes:
Supported `component_kind` values are `resistor`, `capacitor`, `diode`,
`voltage_source`, and `ground`. `ground` is authored as a `GND` net label so it
matches the persisted format already used in the example schematics. Set
`auto_place=true`, call `suggest_component_placement`, or batch-apply a v1 JSON layout
spec via `apply_schematic_layout_spec` to avoid overlapping parts at `(0,0)`.

## apply_schematic_layout_spec

Purpose:
Place schematic components in batch from a workspace JSON layout specification
using `auto`, `grid`, or `absolute` placement modes.

Typical inputs:
- `schematic_path`
- `spec_path` (workspace-local `.json` file)
- `skip_existing` (optional boolean; default true — skip rows whose reference already exists)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `spec_path`
- `output_path`
- `schema_version`
- `applied_count`
- `skipped_existing_count`
- `components` (reference, component_kind, placement, position_x, position_y, rotation_degrees, skipped_existing)

Notes:
Call `describe_schematic_layout_spec` for the v1 schema and bundled
`scratch_power_stage.v1.json` example. Layout spec v1 covers component coordinates
only — add wires, junctions, and labels with dedicated tools afterward.

## add_dll_block

Purpose:
Insert one `.DLL` custom-device block into a schematic and persist the edited
`.qsch` file.

Typical inputs:
- `schematic_path`
- `reference` (required; typically an `X` reference such as `X1`)
- `device_name` (required; written into the value text shown on the symbol)
- `input_pin_names` (optional string list, defaults to `["in0"]`)
- `output_pin_names` (optional string list, defaults to `["out0"]`)
- `position_x` (optional integer)
- `position_y` (optional integer)
- `rotation_degrees` (optional integer, multiple of 45)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `device_name`
- `input_pin_names`
- `output_pin_names`
- `position_x`
- `position_y`
- `rotation_degrees`

Notes:
This is the first blank-start `.DLL` authoring slice. It creates the custom
device symbol directly in the schematic, after which `add_dll_block_pin`,
`remove_dll_block_pin`, `set_dll_block_pin_role`, or the lower-level
`set_component_symbol_pin` tool can refine the symbol.

## add_dll_block_pin

Purpose:
Insert one input or output pin into an existing `.DLL` block symbol and persist
the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `pin_name`
- `direction` (`input` or `output`)
- `insert_index` (optional, within the selected direction group)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `pin`
- `input_pin_names`
- `output_pin_names`

Notes:
This tool keeps the `.DLL` block grouped as inputs first, outputs second, and
reflows the symbol rectangle and pin positions after insertion.

## add_wire

Purpose:
Insert one wire segment into a schematic and persist the edited `.qsch` file.

Typical inputs:
- `schematic_path`
- either `start_x` and `start_y`, or `start_reference` and `start_pin`
- either `end_x` and `end_y`, or `end_reference` and `end_pin`
- `net_name`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `start_x`
- `start_y`
- `end_x`
- `end_y`
- `net_name`

Notes:
This is the lowest-level authoring primitive for connecting placed parts. The
current surface requires an explicit `net_name` so blank-start schematics can be
assembled deterministically. Pin-snapped mode uses component references plus pin
names such as `V1` and `+`, or `R1` and `1`, and returns the resolved absolute
wire coordinates.

## remove_wire

Purpose:
Remove one wire segment from a schematic and persist the edited `.qsch` file.

Typical inputs:
- `schematic_path`
- either `start_x` and `start_y`, or `start_reference` and `start_pin`
- either `end_x` and `end_y`, or `end_reference` and `end_pin`
- `net_name` (optional disambiguator)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `start_x`
- `start_y`
- `end_x`
- `end_y`
- `net_name`

Notes:
Mirrors `add_wire` endpoint resolution. When multiple wires share endpoints,
pass `net_name` to select the intended segment.

## remove_net_label

Purpose:
Remove one net label from a schematic and persist the edited `.qsch` file.

Typical inputs:
- `schematic_path`
- `position_x`
- `position_y`
- `net_name` (optional disambiguator)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `position_x`
- `position_y`
- `net_name`

Notes:
Mirrors `add_net_label`. When multiple labels share a position, pass `net_name`
to select the intended label.

## remove_junction

Purpose:
Remove one junction node from a schematic and persist the edited `.qsch` file.

Typical inputs:
- `schematic_path`
- `position_x`
- `position_y`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `position_x`
- `position_y`

Notes:
Mirrors `add_junction`.

## add_net_label

Purpose:
Insert one net label into a schematic and persist the edited `.qsch` file.

Typical inputs:
- `schematic_path`
- `position_x`
- `position_y`
- `net_name`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `position_x`
- `position_y`
- `net_name`

Notes:
Use this with `add_wire` when building a new schematic from scratch. `GND` uses
the same label style already present in the shipped example circuits.

## inspect_schematic

Purpose:
Provide a read-only summary of the source schematic before any simulation runs.

Typical inputs:
- `schematic_path` (path to a `.qsch` file within the workspace)

Expected outputs:
- `title`
- `analyses`
- `component_count`
- `components` or a condensed component summary
- `warnings` about unsupported or ambiguous constructs

Notes:
This tool should favor inspection over transformation. It is the default entry
point for understanding a project because the repository is intentionally
`qsch` first.

## read_net_connectivity

Purpose:
Report the electrical nets of a supported clean-room `.qsch` and the component
pins attached to each, without mutating the schematic.

Typical inputs:
- `schematic_path` (path to a `.qsch` file within the workspace)

Expected outputs:
- `node_count`
- `component_count`
- `ground_present`
- `nets` (each with `net`, `labeled`, `pin_count`, and `pins` of `{reference, pin}`)

Notes:
Connectivity is derived from the repo-owned clean-room parser, so it covers the
supported schematic subset. Ground nets (`GND`/`0`) normalize to `0`.

## check_schematic

Purpose:
Run read-only ERC-style checks on a supported `.qsch` schematic.

Typical inputs:
- `schematic_path` (path to a `.qsch` file within the workspace)

Expected outputs:
- `ok`
- `error_count`, `warning_count`, `info_count`
- `findings` (each with `severity`, `code`, `message`)

Notes:
Checks include missing ground reference (`missing_ground`), floating pins
(`floating_pin`), duplicate reference designators (`duplicate_reference`),
missing value/model (`missing_value`), and conflicting net labels
(`conflicting_net_labels`). This is a static lint and does not run a simulation.

## check_netlist

Purpose:
Run conservative read-only ERC-style checks on a `.net` or `.cir` netlist body.

Typical inputs:
- `netlist_path` (path to a `.net` or `.cir` file within the workspace)

Expected outputs:
- `ok`
- `error_count`, `warning_count`, `info_count`
- `findings` (each with `severity`, `code`, `message`)

Notes:
Checks include missing ground node `0` (`missing_ground`), duplicate reference
designators (`duplicate_reference`), and single-connection nodes
(`single_connection_node`). Node extraction is heuristic per element type.

## compare_schematics

Purpose:
Diff two supported clean-room `.qsch` schematics.

Typical inputs:
- `base_path` (path to the baseline `.qsch`)
- `revised_path` (path to the revised `.qsch`)

Expected outputs:
- `added_components`, `removed_components`
- `changed_components` (each with `reference`, `field`, `base`, `revised`)
- `base_node_count`, `revised_node_count`
- `identical`

Notes:
Component changes cover `kind`, `value`, `position`, `rotation_degrees`, and
`nodes`. Net differences are surfaced through the node counts.

## move_component_preserving_connections

Purpose:
Move and/or rotate one placed component while keeping its attached wiring intact.

Typical inputs:
- `schematic_path`
- `reference`
- `position_x` / `position_y` (optional; default to the current anchor)
- `rotation_degrees` (optional, multiple of 45)
- `output_path` (optional)

Expected outputs:
- `position_x`, `position_y`, `rotation_degrees`
- `rewired_endpoints` (count of wire/junction/net points moved to follow pins)

Notes:
Pin coordinates are snapshotted before the transform; any wire endpoint,
junction, or net-label point that matched an old pin coordinate is rewritten to
the new coordinate. Provide at least one of `position_x`, `position_y`, or
`rotation_degrees`.

## add_library_component

Purpose:
Clone one component symbol from a reference template `.qsch` into a target
schematic, assigning a new reference designator.

Typical inputs:
- `schematic_path` (target schematic)
- `template_path` (reference schematic to clone from)
- `template_reference` (component reference within the template)
- `reference` (new reference designator in the target)
- `position_x` / `position_y` (optional placement; default `(0, 0)`)
- `value` (optional override; defaults to the template value)
- `output_path` (optional)

Expected outputs:
- `reference`, `symbol_name`, `type_name`, `library_file`, `value`
- `pin_names`

Notes:
This is a clean-room template clone: the full symbol subtree (symbol name,
`library file:`, drawing primitives, and pins) is deep-copied, so no `.asy`
library parser is required.

## render_schematic_image

Purpose:
Render a supported `.qsch` schematic to a PNG preview image.

Typical inputs:
- `schematic_path`
- `output_path` (optional)
- `overwrite` (optional)

Expected outputs:
- `image_path`, `format`
- `component_count`, `wire_count`, `net_label_count`

Notes:
The render draws wire segments, junction dots, component pins and
refdes/value labels, and net labels parsed from the clean-room subset. It uses
the same matplotlib dependency as `plot_waveforms`.

## list_components

Purpose:
Enumerate normalized component summaries from a schematic through an installed
`QschEditor` backend or the supported clean-room subset.

Typical inputs:
- `schematic_path`
- `prefixes` (optional string filter such as `R`, `CV`, or `*`)

Expected outputs:
- `schematic_path`
- `component_count`
- `prefixes`
- `components`

Notes:
This is the low-cost discovery companion to `read_component`. It returns a
stable summary shape even though the underlying editor backend may expose a
much larger and less stable internal component object. When no optional editor
backend is installed, the tool still works for the supported clean-room
schematic subset, including base-install blank and starter schematics.

## read_component

Purpose:
Return a normalized view of one component, including connected nodes, parsed
parameters, raw parameter text lines, and placement metadata.

Typical inputs:
- `schematic_path`
- `reference`

Expected outputs:
- `schematic_path`
- `reference`
- `kind`
- `value`
- `description`
- `nodes`
- `parameters`
- `raw_parameter_lines`
- `position_x`
- `position_y`
- `rotation_degrees`
- `has_subcircuit`

Notes:
The backing `QschEditor` API exposes parser-internal attributes that are not a
good public contract. This tool normalizes those details into a repo-owned
result shape instead of exposing backend objects directly. When no optional
editor backend is installed, the tool still works for the supported clean-room
schematic subset, including the base-install starter topology and other
schematics that stay within the same conservative parser subset.

## read_component_symbol

Purpose:
Return a normalized view of one component's embedded symbol metadata,
including text attributes, typed pins, normalized drawing items, drawing tags,
and image-asset tokens.

Typical inputs:
- `schematic_path`
- `reference`

Expected outputs:
- `schematic_path`
- `reference`
- `symbol_name`
- `type_name`
- `description`
- `library_file`
- `shorted_pins`
- `text_attributes`
- `pins`
- `drawing_items`
- `drawing_tags`
- `image_asset_tokens`

Notes:
This surface stays backend-backed on purpose. It exposes repo-owned metadata
records instead of leaking raw `QschTag` internals into the MCP contract.

## add_component_symbol_drawing

Purpose:
Insert one embedded symbol drawing item and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `tag_name`
- `arguments`
- `insert_index` (optional)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `drawing_item`

Notes:
`tag_name` is limited to symbol drawing tags; symbol metadata, text, and pin
tags stay on their dedicated tools. `arguments` are raw QSch token strings,
so callers can express shape-specific geometry without backend-specific Python
objects.

## set_component_symbol_drawing

Purpose:
Update one embedded symbol drawing item and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `drawing_index`
- `tag_name` (optional)
- `arguments` (optional)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `drawing_item`

Notes:
At least one of `tag_name` or `arguments` must be supplied. This tool replaces
the selected raw drawing tag with the requested normalized repo-owned shape.

## set_component_symbol_text

Purpose:
Update one embedded symbol text item and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `text_index` or `text_role`
- `text` (optional)
- `position_x` and `position_y` (optional, must be supplied together)
- `size` (optional)
- `rotation_code` (optional)
- `is_comment` (optional)
- `color_code` (optional)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `text_attribute`

Notes:
At least one editable attribute must be supplied. Reference-designator text content
is not rewritten through this tool; use `rename_component_reference` instead.
For layout readability after symbol body rotation, prefer
`normalize_component_text_rotation` (compensates body rotation automatically).
Use this tool for manual per-item text layout when you need explicit
`position_x`/`position_y`, `size`, or non-default `rotation_code` values.

## normalize_component_text_rotation

Purpose:
Reset embedded refdes/value symbol text to left-to-right readable orientation,
optionally compensating for the placed component body rotation.

Typical inputs:
- `schematic_path`
- `reference`
- `text_roles` (optional; default `["reference", "value"]`; accepts `refdes` alias)
- `compensate_component_rotation` (optional; default `true`)
- `upright_rotation_code` (optional; used when `compensate_component_rotation` is `false`)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `component_rotation_degrees`
- `compensate_component_rotation`
- `target_rotation_code`
- `updated_count`
- `skipped_count`
- `text_attributes` (per-role previous/new rotation codes and update flags)

Notes:
Symbol body rotation (`set_component_rotation`) does not update embedded text or
wire endpoints. With `compensate_component_rotation=true` (default), the tool
sets text rotation codes so labels read horizontal in world space (for example,
body at 90° targets rotation code **109**). Factory-default text codes on
0°-placed parts are left unchanged. Does not move wire segments — refresh wires
separately after layout moves.

## rename_component_reference

Purpose:
Rename one schematic component reference, updating both the component object
and its embedded symbol REFDES text in one atomic operation.

Typical inputs:
- `schematic_path`
- `reference` (current reference)
- `new_reference` (target reference, case-insensitive uniqueness enforced)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `new_reference`

Notes:
The new reference must not already exist in the schematic. The tool updates
the component object reference, the embedded symbol REFDES text, and the
internal editor dictionary so subsequent reads and edits resolve correctly.

## describe_edit_capability

Purpose:
Preflight one edit intent on a specific component: read its current state, map
the intent to the correct tool, and return a go/no-go decision with the nearest
valid alternatives.

Typical inputs:
- `schematic_path`
- `reference`
- `intent` (one of `rename_reference`, `change_value`, `change_model`,
  `edit_parameters`, `rotate_component`, `edit_symbol_text`, `edit_symbol_pin`,
  `edit_symbol_drawing`, `delete_component`)

Expected outputs:
- the resolved target tool for the intent
- a go/no-go readiness flag
- current component state relevant to the edit
- suggested alternatives when the intent does not apply

Notes:
Read-only. This is the per-component companion to the static
`describe_schematic_edit_support` map and is intended for AI clients that want to
confirm an edit is valid before issuing a mutating call.

## describe_schematic_edit_support

Purpose:
Return a static machine-readable capability map of every known schematic edit
intent so clients can make deterministic go/no-go decisions before writing.

Typical inputs:
- none

Expected outputs:
- per-intent capability entries with the owning tool and constraints

Notes:
Read-only and component-independent. Use `describe_edit_capability` when you
need the same decision evaluated against one specific component.

## describe_schematic_layout_spec

Purpose:
Return the v1 JSON layout-spec schema, supported placement modes, and a bundled
example document for batch component placement without large coordinate tables.

Typical inputs:
- none

Expected outputs:
- `schema_version`
- `placement_modes` (`auto`, `grid`, `absolute`)
- `json_schema`
- `example_document`
- `bundled_example_path`
- `notes`

Notes:
Write a workspace JSON file matching the schema and pass its path to
`apply_schematic_layout_spec`. `placement=auto` uses the same collision-aware grid
as `suggest_component_placement`. Wires, junctions, and labels are not part of v1.

## set_component_symbol_pin

Purpose:
Update one embedded symbol pin item and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `pin_index` or `pin_name`
- `new_pin_name` (optional)
- `label_position_x` and `label_position_y` (optional, must be supplied together)
- `text_size` (optional)
- `label_anchor_code` (optional)
- `pin_kind_code` (optional)
- `color_code` (optional)
- `aux_code` (optional)
- `behavioral_net_override` (optional)
- `clear_behavioral_net_override` (optional boolean)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `pin`

Notes:
At least one pin attribute update must be supplied. Setting and clearing the
behavioral net override in the same call is rejected. This also works on
`.DLL` block symbols created through `add_dll_block`, but for higher-level
input/output role changes on `.DLL` blocks prefer `set_dll_block_pin_role`.

## set_dll_block_pin_role

Purpose:
Move one `.DLL` block pin into the input or output role preset and persist the
edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `pin_role` (`input` or `output`)
- exactly one of `pin_index` or `pin_name`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `pin`
- `input_pin_names`
- `output_pin_names`

Notes:
This is the higher-level `.DLL` pin-type surface. It moves the selected pin to
the chosen direction group and reapplies the corresponding symbol-side layout
instead of forcing callers to manipulate raw pin-kind codes directly.

## remove_dll_block_pin

Purpose:
Remove one pin from an existing `.DLL` block symbol and persist the edited
schematic.

Typical inputs:
- `schematic_path`
- `reference`
- exactly one of `pin_index` or `pin_name`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `removed_pin_name`
- `input_pin_names`
- `output_pin_names`

Notes:
This tool keeps the remaining pins grouped and reflowed after removal. It
rejects edits that would leave the `.DLL` block with zero pins.

## remove_component

Purpose:
Remove one schematic component by reference and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `removed`

Notes:
This deletes the component object and its embedded symbol. Wires, junctions, and
net labels are not rerouted automatically, so review connectivity afterward with
`inspect_schematic` or `list_components`. Use `describe_edit_capability` with
intent `delete_component` for a preflight go/no-go check.

## remove_component_symbol_drawing

Purpose:
Remove one embedded symbol drawing item and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `drawing_index`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `drawing_item`

Notes:
The returned `drawing_item` is the removed record so callers can inspect or
reinsert the deleted geometry if needed.

## save_schematic_as

Purpose:
Write a `.qsch` file to a requested destination path through an installed
editor backend.

Typical inputs:
- `schematic_path`
- `output_path`

Expected outputs:
- `schematic_path`
- `output_path`

Notes:
This is an explicit file-copy/save tool for workflows that want a separate
edited artifact instead of mutating the source file in place.

## set_component_value

Purpose:
Update the value field of one component and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `value`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `value`

## set_component_rotation

Purpose:
Rotate one placed schematic component without changing its `(x, y)` position.

Typical inputs:
- `schematic_path`
- `reference`
- `rotation_degrees` (multiple of 45, e.g. `0`, `90`, `180`, `270`)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `rotation_degrees`

Notes:
Pin world coordinates depend on rotation; **wire segments are not moved with the
symbol**. After rotating, remove stale segments with `remove_wire` and re-add with
`add_wire` using pin selectors on the same `net_name`. **Refdes/value text rotates
with the symbol** — run a readability pass with `read_component_symbol` and
`set_component_symbol_text(..., rotation_code=13)` on `refdes` and `value` roles.
`read_component` reports component `rotation_degrees`; symbol text uses separate
`rotation_code` on each embedded text item.

## set_component_position

Purpose:
Move one placed schematic component to new grid coordinates, optionally updating
its rotation in the same edit.

Typical inputs:
- `schematic_path`
- `reference`
- `position_x`
- `position_y`
- `rotation_degrees` (optional; multiple of 45)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `position_x`
- `position_y`
- `rotation_degrees`

Notes:
**Wire segments are not moved with the symbol.** After moving, remove affected
segments with `remove_wire` and reconnect with `add_wire` (pin selectors +
`net_name`). When `rotation_degrees` is omitted the existing rotation is preserved.
Prefer final placement before wiring when building from scratch.

## suggest_component_placement

Purpose:
Suggest collision-free schematic coordinates for the next component using a
readable left-to-right grid with upright (0°) rotation.

Typical inputs:
- `schematic_path`
- `component_kind`
- `origin_x` / `origin_y` (optional grid start; default 400,400)
- `grid_step_x` / `grid_step_y` (optional; default 400)
- `clearance_units` (optional extra separation margin)
- `max_columns` / `max_rows` (optional scan limits)

Expected outputs:
- `schematic_path`
- `component_kind`
- `position_x`
- `position_y`
- `rotation_degrees` (0 unless you override at `add_component` time)
- `grid_step_x`
- `grid_step_y`
- `clearance_units`
- `existing_component_count`
- `notes`

Notes:
Uses conservative symbol footprints — verify dense layouts in the GUI. For full
buck scratch builds, prefer coordinate tables from
`read_workflow_instruction(instruction_id="buck-converter-cpp")`. Pair with
`add_component(..., auto_place=true)` to place and persist in one step.

## set_component_parameters

Purpose:
Update one or more component-local parameters and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `parameters`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `parameter_names`

Notes:
The underlying editor backend supports a mixed integer-key/string-key API for
parameter text editing. This tool intentionally exposes only named parameter
updates.

## set_element_model

Purpose:
Update the model text of one component and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `reference`
- `model`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `reference`
- `model`

## set_parameter

Purpose:
Update one schematic-level `.param` directive and persist the edited schematic.

Typical inputs:
- `schematic_path`
- `name`
- `value`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `name`
- `value`

## list_subcircuits

Purpose:
Enumerate subcircuit instances from a schematic and indicate whether their
definitions resolve.

Typical inputs:
- `schematic_path`
- `instance_path` (optional parent subcircuit path)

Expected outputs:
- `schematic_path`
- `instance_path`
- `subcircuit_count`
- `subcircuits` (list with `reference`, `definition`, `resolved`)

Notes:
Without `QschEditor`, this tool still works for the supported clean-room
subset by following `X*` instance values to external `.qsch` definitions in
the parent schematic directory or by workspace-relative path. Nested
`instance_path` traversal works on that same external-definition path.
Embedded, `library file`-backed, or otherwise non-file-resolved subcircuits
still require the optional editor backend and will report unresolved
definitions or path-resolution errors.

## read_subcircuit

Purpose:
Return a resolved view of one subcircuit instance or definition, including
its nested component summaries.

Typical inputs:
- `schematic_path`
- `reference`
- `instance_path` (optional parent subcircuit path)
- `scope` (optional, `instance` or `definition`; defaults to `instance`)

Expected outputs:
- `schematic_path`
- `instance_path`
- `reference`
- `scope`
- `definition`
- `component_count`
- `components`

Notes:
Use `instance_path` to descend through nested subcircuit instances before
selecting the final `reference`. Instance scope returns the subcircuit as
placed in the parent schematic. Definition scope resolves the subcircuit
definition block, which may expose a different component inventory. Without
`QschEditor`, the clean-room fallback can still follow external `.qsch`
definitions in the parent schematic directory or by workspace-relative path,
including nested `instance_path` chains, but instance scope reads that
resolved definition schematic directly rather than performing backend-only
instance expansion, and embedded or library-backed subcircuits still require
the optional editor backend.

## set_subcircuit_component_value

Purpose:
Update one nested component value inside a subcircuit instance or definition.

Typical inputs:
- `schematic_path`
- `subcircuit_reference`
- `instance_path` (optional parent subcircuit path)
- `component_reference`
- `value`
- `scope` (optional, `instance` or `definition`; defaults to `instance`)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `instance_path`
- `subcircuit_reference`
- `component_reference`
- `scope`
- `value`

Notes:
For instance-scoped edits, `instance_path` and `subcircuit_reference` are
combined into the hierarchical selector written back to the parent schematic.
For definition-scoped edits, the same nested path is resolved first and the
definition editor is then saved explicitly.

## set_subcircuit_component_parameters

Purpose:
Update nested component parameters inside a subcircuit instance or definition.

Typical inputs:
- `schematic_path`
- `subcircuit_reference`
- `instance_path` (optional parent subcircuit path)
- `component_reference`
- `parameters`
- `scope` (optional, `instance` or `definition`; defaults to `instance`)
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `instance_path`
- `subcircuit_reference`
- `component_reference`
- `scope`
- `parameter_names`

Notes:
Nested `instance_path` segments are resolved before the target subcircuit is
edited, so the same contract works for top-level and deeper hierarchy paths.

## add_instruction

Purpose:
Append one analysis instruction line to a schematic using `instruction=`.

Typical inputs:
- `schematic_path`
- `instruction`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `output_path`
- `instruction`

## remove_instruction

Purpose:
Remove one exact or regex-matched directive from a schematic.

Typical inputs:
- `schematic_path`
- `instruction`
- `output_path` (optional)
- `regex` (optional boolean)

Expected outputs:
- `schematic_path`
- `output_path`
- `instruction`
- `regex`

## generate_netlist

Purpose:
Resolve or stage the derived netlist that will be used for execution.

Typical inputs:
- `source_path`
- `output_path` (optional)

Expected outputs:
- `netlist_path`
- `source_path`
- `source_kind`
- `copied`
- `warnings`
- `netlist_backend` (optional: `qux`, `clean_room`, `editor`, or `existing`)

Notes:
This tool first resolves or stages an existing derived `.net` or `.cir`
artifact. When regeneration is required, schematics that contain `.DLL`,
Verilog, or C-block components prefer companion `QUX.exe -Netlist` when
`QSPICE_EXE` resolves. Otherwise it uses the repo-owned clean-room `.qsch`
parser (which omits DLL blocks and may warn) and then an installed
`QschEditor` backend for broader coverage. Existing sidecars that omit required
DLL instance lines are treated as stale and refreshed when QUX is available.

## list_includes

Purpose:
List `.include`, `.inc`, and `.lib` directives reachable from one netlist root.

Typical inputs:
- `netlist_path`

Expected outputs:
- `netlist_path`
- `include_count`
- `missing_count`
- `includes` (each with `kind`, `directive`, `raw_path`, `resolved_path`, `exists`, `source_netlist`)

## resolve_model_libraries

Purpose:
Resolve `.lib` model-library paths referenced by one netlist graph.

Typical inputs:
- `netlist_path`

Expected outputs:
- `netlist_path`
- `library_count`
- `missing_count`
- `libraries` (each with `raw_path`, `resolved_path`, `exists`, `source_netlist`)
- `warnings`

Notes:
Missing libraries are summarized in `warnings`. Resolved include files also
participate in simulation cache key hashing during `run_simulation`.

## add_library_include

Purpose:
Append one `.include`, `.inc`, or `.lib` directive before the netlist `.end`
marker.

Typical inputs:
- `netlist_path`
- `include_path` (workspace-local library file that must already exist)
- `kind` (`include`, `inc`, or `lib`; default `include`)
- `output_path` (optional staged copy)
- `relative_to_netlist` (default `true`)

Expected outputs:
- `source_netlist`
- `output_netlist`
- `include_path`
- `directive`
- `already_present` (always `false` on success)

Notes:
Duplicate directives for the same resolved path raise `validation_error`.

## add_model

Purpose:
Append one SPICE model definition block to a `.lib`, `.inc`, or netlist file.

Typical inputs:
- `target_path`
- `model_text` (multiline `.model` or subcircuit body)
- `output_path` (optional staged copy)

Expected outputs:
- `source_path`
- `output_path`
- `model_name` (best-effort guess from the first model token)
- `line_count`

Notes:
`model_text` must not contain a standalone `.end` directive.

## save_netlist_copy

Purpose:
Resolve or generate one derived netlist artifact and save it to an explicit
destination path.

Typical inputs:
- `source_path`
- `output_path`

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `refreshed`
- `copied`
- `warnings`

Notes:
This is the explicit copy-oriented companion to `generate_netlist`. Use it
when the workflow needs a concrete saved `.net` or `.cir` artifact at a known
path instead of the default derived sidecar location.

## run_simulation

Purpose:
Plan or run QSpice for a `.qsch`, `.cir`, or `.net` source path and return
stable metadata about the resolved command and, when executed, the result.

Typical inputs:
- `source_path`
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `log_path` (optional derived artifact override)
- `raw_output_path` (optional derived artifact override)
- `netlist_output_path` (optional derived netlist override for schematic inputs)
- `ascii_raw` (optional boolean)
- `extra_switches` (optional validated CLI switches)
- `run_id` (optional caller-supplied identifier enabling `cancel_run`)

Expected outputs:
- `source_path`
- `adapter_key`
- `command`
- `working_directory`
- `dry_run`
- `duration_s`
- `raw_path`
- `log_path`
- `exit_code`
- `stdout`
- `stderr`
- `cached`
- `cache_key`
- `generated_netlist` (present for schematic inputs)
- `warnings`

Failure modes:
- `AdapterNotFoundError`
- `SandboxViolationError`
- `SimulationTimeoutError`
- `SimulationError`
- `ConvergenceError`

Notes:
The underlying application service remains netlist-first, but the MCP tool is
schematic-aware: when `source_path` points to a `.qsch`, the handler calls
`generate_netlist` first and then runs the derived netlist through the existing
simulation service. DLL-bearing schematics (for example the bundled
`buck_converter_cpp` recipe) require a built sibling `.dll` and QUX-backed
netlist generation when `QSPICE_EXE` is configured. Successful runs are cached transparently by stable netlist
content plus execution-switch context, and later matching requests materialize
the cached `.log`/`.qraw` pair instead of rerunning QSpice. Failed or timed-out
executions restore any previous `.log` or `.qraw` artifact that existed at the
requested output paths so partial replacement files are not left behind.

When a caller supplies `run_id`, the in-flight process is tracked so a
concurrent `cancel_run` request with the same identifier can terminate it.

## cancel_run

Purpose:
Request cancellation of an in-flight `run_simulation` invocation by the
caller-supplied `run_id`, terminating the tracked QSpice process.

Typical inputs:
- `run_id` (the identifier passed to the in-flight `run_simulation` call)

Expected outputs:
- `run_id`
- `cancelled`

Failure modes:
- `ValidationError` (blank `run_id`, or no active run is tracked for `run_id`)

Notes:
Cancellation is only possible while the run is executing; once the process has
exited or was never started with that `run_id`, the request fails. The cancelled
`run_simulation` call raises `SimulationError` to report the interruption.

## run_value_sweep

Purpose:
Run one schematic across multiple component values, executing each variant
as a separate QSpice run with bounded parallelism.

Typical inputs:
- `schematic_path`
- `reference`
- `values` (list of value strings)
- `output_dir` (optional)
- `resume` (optional boolean)
- `retain_artifacts` (optional, one of `none`, `all`, `failed`)
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `extra_switches` (optional validated CLI switches)

Expected outputs:
- `batch_id`
- `status`
- `reference`
- `run_count`
- `resumed`
- `retain_artifacts`
- `dry_run`
- `manifest_path`
- `runs` (list of per-run metadata when synchronous)

Notes:
This is a synchronous convenience wrapper around `submit_batch` with
`batch_kind=value`. It blocks until all runs complete or the combined
timeout elapses. For background execution, use `submit_batch` directly.
The `schematic_path` must be a `.qsch` source; `.net`/`.cir` inputs are
rejected because clean-room netlist editing for sweeps is not yet implemented.

## run_param_sweep

Purpose:
Run one schematic across the Cartesian product of parameter values with
bounded parallelism.

Typical inputs:
- `schematic_path`
- `parameters` (mapping of parameter name → list of values)
- `output_dir` (optional)
- `resume` (optional boolean)
- `retain_artifacts` (optional, one of `none`, `all`, `failed`)
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `extra_switches` (optional validated CLI switches)

Expected outputs:
- `batch_id`
- `status`
- `parameter_names`
- `run_count`
- `resumed`
- `retain_artifacts`
- `dry_run`
- `manifest_path`
- `runs` (list of per-run metadata when synchronous)

Notes:
The Cartesian product of all parameter lists determines the run count. Each
run edits the schematic with the assigned `.param` combination via a
factory-produced closure, executes QSpice on the edited copy, and records
results in the batch manifest.
The `schematic_path` must be a `.qsch` source; `.net`/`.cir` inputs are
rejected because clean-room netlist editing for sweeps is not yet implemented.

## run_model_sweep

Purpose:
Run one schematic across multiple element models with bounded parallelism.

Typical inputs:
- `schematic_path`
- `reference`
- `models` (list of model strings)
- `output_dir` (optional)
- `resume` (optional boolean)
- `retain_artifacts` (optional, one of `none`, `all`, `failed`)
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `extra_switches` (optional validated CLI switches)

Expected outputs:
- `batch_id`
- `status`
- `reference`
- `run_count`
- `resumed`
- `retain_artifacts`
- `dry_run`
- `manifest_path`
- `runs` (list of per-run metadata when synchronous)

Notes:
Each run edits the referenced component's model text before execution.
This is useful for comparing device model variants (e.g., different MOSFET
or op-amp models) under identical operating conditions.
The `schematic_path` must be a `.qsch` source; `.net`/`.cir` inputs are
rejected because clean-room netlist editing for sweeps is not yet implemented.

## submit_remote_simulation

Purpose:
Submit one remote-style single-run session for background execution inside the
configured workspace.

Typical inputs:
- `source_path`
- `output_dir` (optional)
- `dry_run` (optional boolean)
- `timeout_s` (optional)
- `ascii_raw` (optional boolean)
- `extra_switches` (optional validated CLI switches)

Expected outputs:
- `session_id`
- `status`
- `source_path`
- `output_root`
- `submitted_at`
- `owner_host_id`

Notes:
This remains a workspace-backed transport layer rather than a network fabric,
but the persisted session summary now carries host ownership metadata as well
as lease timestamps. Later server instances on the same or a different host
can inspect the shared registry, keep fresh foreign-host sessions live, and
fail stale nonterminal sessions once the owning host stops refreshing its
lease. New remote sessions still require an empty output root so one session
cannot reuse another session's retained files.

## poll_remote_run

Purpose:
Read live or terminal status for one submitted remote-style session.

Typical inputs:
- `session_id`

Expected outputs:
- `session_id`
- `status`
- `source_path`
- `output_root`
- `submitted_at`
- `completed_at`
- `simulation_input_path`
- `log_path`
- `raw_path`
- `bundle_path`
- `dry_run`
- `exit_code`
- `duration_s`
- `log_available`
- `raw_available`
- `bundle_available`
- `owner_host_id`
- `lease_heartbeat_at`
- `error`

Notes:
The status values are `queued`, `running`, `completed`, `failed`, and
`closed`. A completed or failed session can still produce a useful zip bundle
when logs or staged netlists exist. Terminal sessions can be polled again from
later server instances because the manager state is persisted in the workspace.
`owner_host_id` identifies which host most recently refreshed the session
lease, while `lease_heartbeat_at` records the latest persisted heartbeat. If a
reloaded nonterminal session has lost its same-host owner process or its
host-scoped lease has expired, the manager now fails it closed as an orphan
instead of reporting a stale live state indefinitely.

## download_remote_artifacts

Purpose:
Package selected remote-style session artifacts into one zip bundle.

Typical inputs:
- `session_id`
- `output_path` (optional)
- `artifact_kinds` (optional list from `summary`, `source`, `netlist`, `log`, `raw`)

Expected outputs:
- `session_id`
- `status`
- `output_path`
- `artifact_kinds`
- `entry_names`
- `artifact_count`
- `bundle_size_bytes`

Notes:
When `artifact_kinds` is omitted, the bundle defaults to `summary`, `netlist`,
`log`, and `raw`. The summary entry is always a `session.json` payload that
captures the persisted session metadata tracked by the manager.

## close_remote_session

Purpose:
Close one remote-style session and optionally delete its staged zip bundle.

Typical inputs:
- `session_id`
- `delete_bundle` (optional boolean)

Expected outputs:
- `session_id`
- `status`
- `output_root`
- `bundle_deleted`
- `note`

Notes:
Closing a session does not remove the session output directory or simulation
artifacts. It marks the persisted session record as closed and, when requested,
deletes the staged zip bundle created by `download_remote_artifacts`.

## summarize_batch

Purpose:
Summarize one persisted batch manifest and its derived artifacts.

Typical inputs:
- `manifest_path`

Expected outputs:
- `batch_id`
- `batch_kind`
- `status`
- `run_count`
- `completed`
- `failed`
- `schematic_path`
- `output_dir`
- `schema_version`
- `runs` (compact per-run summary: index, label, exit_code, log_path, raw_path, error)
- `warnings`

Notes:
This is the primary inspection tool for completed or in-progress batch
artifacts. It re-validates manifest paths against the active workspace
before returning them.

## export_measures_csv

Purpose:
Flatten measurement rows from a persisted batch manifest into CSV.

Typical inputs:
- `manifest_path`
- `output_path` (optional)

Expected outputs:
- `manifest_path`
- `output_path`
- `row_count`
- `measure_count`

Notes:
QPOST `.meas` results from each completed run are flattened into a single
CSV with columns for run index, run label, measure name, and measure value.
Runs without `.meas` data are skipped.

## compare_waveforms

Purpose:
Compare one scalar waveform measurement across runs in a persisted batch.

Typical inputs:
- `manifest_path`
- `signal`
- `measure` (e.g., `max`, `min`, `mean`, `rms`, `pp`)
- `step` (optional)
- `step_filters` (optional)

Expected outputs:
- `manifest_path`
- `signal`
- `measure`
- `run_count`
- `compared`
- `results` (list of `{ run_index, run_label, value }`)
- `min_run`
- `max_run`
- `warnings`

Notes:
Each run's `.qraw` artifact is opened and the requested scalar measurement
is extracted from the named signal. Runs whose raw artifact is missing or
whose signal does not exist are reported in `warnings` and excluded from
the comparison.

## list_steps

Purpose:
Enumerate simulation step indices and, when a sibling `.log` file is present,
recover the corresponding `.step` variable assignments.

Typical inputs:
- `raw_path`

Expected outputs:
- `raw_path`
- `log_path`
- `step_count`
- `step_variables`
- `steps`
- `warnings`

Notes:
This is the bridge between a stepped `.qraw` artifact and user-facing step
selection. It degrades gracefully when the raw artifact advertises multiple
steps but no sibling `.log` file is available to recover parameter labels.

## list_signals

Purpose:
Enumerate signal names and basic metadata without returning waveform samples.

Typical inputs:
- `raw_path`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)

Expected outputs:
- `raw_path`
- `plot_name`
- `axis_name`
- `axis_unit`
- `resolved_step`
- `step_count`
- `point_count`
- `signal_count`
- `signals`
- `warnings`

Notes:
This tool is intentionally lighter weight than `read_waveform` and should be
preferred when the user is still exploring available outputs. Some backends can
advertise alias-like trace names that they cannot later materialize as numeric
series, so this tool may return heuristic metadata plus a warning for those
entries instead of failing the entire signal catalog. When `step_filters` are
provided, the tool resolves one concrete step first and reports metadata for
that selected step.

## read_waveform

Purpose:
Return a bounded waveform slice for a single signal.

Typical inputs:
- `raw_path`
- `signal`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `t_start` (optional)
- `t_end` (optional)
- `max_points` (optional override within allowed budget)
- `max_bytes` (optional override within allowed budget)

Expected outputs:
- `signal`
- `step`
- `component`
- `x_values`
- `y_values`
- `x_unit`
- `y_unit`
- `downsampled`
- `original_point_count`
- `complex_source`

Notes:
The service backing this tool should always apply a `DataBudget`; full raw data
is not a supported MCP response shape. Complex traces are projected to a
single real-valued series through the requested `component`, with `auto`
defaulting to magnitude for complex data and real values for real traces.
`step_filters` provide a step-aware alternative to manual numeric step indices.

## evaluate_waveform_expression

Purpose:
Evaluate an arithmetic expression over one or more `.qraw` signals and return a
budgeted result series (for example `V(out)-V(in)` or `V(out)*I(L1)`).

Typical inputs:
- `raw_path`
- `expression` (signal tokens like `V(out)`, numeric constants, parentheses, and `+ - * / **`)
- `step` (optional)
- `step_filters` (optional)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `t_start` / `t_end` (optional)
- `max_points` / `max_bytes` (optional override within allowed budget)

Expected outputs:
- `expression`
- `signals` (resolved signal names referenced by the expression)
- `x_values`, `y_values`
- `x_unit`
- `point_count`, `original_point_count`, `downsampled`

Notes:
The expression is parsed with a restricted AST evaluator (no `eval`); only
signal tokens, numeric constants, parentheses, and the `+ - * / **` operators
are allowed. All referenced signals must share one axis (same raw, step, and
window). The standard `read_waveform` budget caps the response.

## measure_waveform

Purpose:
Return scalar or low-cardinality measurements derived from one or more signals.

Typical inputs:
- `raw_path`
- `signal`
- `operation` such as `min`, `max`, `mean`, `rms`, `peak_to_peak`, `abs_max`, `start`, `end`, or `integral`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- Optional window parameters

Expected outputs:
- `value`
- `y_unit`
- `operation`
- `sample_count`
- `component`

Notes:
Measurements are usually a better fit for MCP than raw arrays because they
compress simulation results into decision-ready values. This tool is
intentionally limited to robust scalar operations over one selected signal
component; higher-level Bode, THD, and FFT workflows now live in dedicated
tools with their own windowing and artifact contracts. Like `read_waveform`,
this tool can resolve stepped runs by explicit index or by `step_filters`.

## plot_waveforms

Purpose:
Generate a plot artifact for one or more signals while keeping the structured
response small.

Typical inputs:
- `raw_path`
- `signals`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `t_start` and `t_end` (optional)
- `fmt` such as `png` or `svg`
- `max_points` and `max_bytes` (optional)
- `output_path` (optional)
- `title` (optional)

Expected outputs:
- `plot_path`
- `signals`
- `format`
- `title`
- `point_count`
- `downsampled`
- `warnings`

Notes:
Plots are derived artifacts. The response should primarily return metadata and a
path, not embed large binary content inline. The current implementation renders
time/frequency-domain line plots from the same bounded waveform pipeline used by
`read_waveform`, so large traces are downsampled before plotting. Stepped runs
can be targeted either by numeric step index or by `step_filters`.

## read_device_operating_points

Purpose:
Read one `Operating Point` `.qraw` artifact and group scalar device metrics by
reference while preserving node voltages and optional sibling-netlist metadata.

Typical inputs:
- `raw_path`
- `netlist_path` (optional explicit `.net` or `.cir` path)

Expected outputs:
- `plot_name`
- `netlist_path`
- `device_count`
- `node_count`
- `groups`
- `devices`
- `node_voltages`
- `warnings`

Notes:
This tool is the detailed operating-point read surface. It expects an `Operating Point`
raw artifact and uses sibling netlist metadata when available to enrich each
device with nodes, model name, and model type. `KEEPOPINFO` and `SAVEPOWERS`
make currents and dissipation available as scalar traces in QSpice's raw data.

## filter_device_operating_points

Purpose:
Filter one operating-point device catalog by inferred family, explicit model,
reference name, reference regex, or required metric names.

Typical inputs:
- `raw_path`
- `netlist_path` (optional)
- `families` (optional list such as `mosfet` or `diode`)
- `models` (optional list such as `NMOS`)
- `references` (optional exact reference list)
- `reference_pattern` (optional regex)
- `metric_names` (optional list such as `power` or `drain_current`)

Expected outputs:
- `original_device_count`
- `device_count`
- `groups`
- `devices`
- `applied_filters`
- `warnings`

Notes:
This is the discovery-to-selection companion for `read_device_operating_points`.
It does not recompute operating-point data; it filters the already normalized
device catalog returned from the same underlying raw artifact.

## summarize_device_operating_points

Purpose:
Return a compact operating-point summary suitable for quick debug and ranking,
without returning every per-device metric first.

Typical inputs:
- `raw_path`
- `netlist_path` (optional)

Expected outputs:
- `device_count`
- `node_count`
- `family_summaries`
- `highest_dissipation`
- `lowest_dissipation`
- `largest_abs_current`
- `highest_node_voltage`
- `lowest_node_voltage`
- `warnings`

Notes:
This tool is intended for compact decision-oriented summaries. It aggregates the
same operating-point data into family counts, total dissipation per
family, and a few useful extrema such as the hottest device or the largest
current magnitude.

## read_log

Purpose:
Expose a concise, user-readable slice of simulator diagnostics and optional
QPOST-derived measurement data.

Typical inputs:
- `run_id` or `log_path`
- `max_lines` (optional)
- `include_measures` (optional)
- `refresh_measures` (optional)
- `meas_path` (optional)
- `timeout_s` (optional QPOST refresh timeout)

Expected outputs:
- `excerpt`
- `line_count`
- `step_count`
- `step_variables`
- `measures`
- `meas_path`
- `qpost_command`
- `warnings`

Notes:
This tool is especially important when a simulation fails, times out, or shows
convergence issues. When measure extraction is enabled, it follows the current
QSpice companion-tool path by invoking `QPOST.exe` next to `QSPICE64.exe`,
staging refreshed `.meas` output through a temporary file so failed refreshes
do not replace the last known artifact in place.

## read_fourier

Purpose:
Parse native QSpice `.four` Fourier summaries from a simulation `.log` file.
Distinct from recomputed FFT tools such as `compute_thd` and `export_fft_spectrum`.

Typical inputs:
- `log_path`

Expected outputs:
- `log_path`
- `analyses` (list of `{ node, dc_component, total_harmonic_distortion_pct, harmonics }`)
- `warnings`

Notes:
Returns one analysis block per `.four` node/expression found in the log. Harmonic
rows include frequency, magnitude, and phase in degrees.

## read_noise

Purpose:
Parse integrated and spot `.noise` summary lines from a simulation `.log` file.

Typical inputs:
- `log_path`

Expected outputs:
- `log_path`
- `summaries` (list of `{ label, value, unit, node?, frequency? }`)
- `warnings`

Notes:
Captures common integrated RMS noise and spot noise density lines emitted by
QSpice after a `.noise` analysis. Spectral `.qraw` plots remain available via
`list_signals` and `read_waveform`.

## list_measures

Purpose:
Enumerate the available QPOST-derived measurement blocks for one simulation
log without returning every value row.

Typical inputs:
- `log_path`
- `refresh_measures` (optional)
- `meas_path` (optional)
- `timeout_s` (optional QPOST refresh timeout)

Expected outputs:
- `log_path`
- `meas_path`
- `step_count`
- `measure_count`
- `measures`
- `warnings`

Notes:
This is the discovery-oriented companion to `read_measures`. It is useful when
the user wants to see which named `.meas` blocks are present before selecting a
subset to read.

## read_measures

Purpose:
Return structured measurement rows from one simulation log, with optional
filtering by measure name, step index, or step-variable assignments.

Typical inputs:
- `log_path`
- `measures` (optional list of measure names)
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `refresh_measures` (optional)
- `meas_path` (optional)
- `timeout_s` (optional QPOST refresh timeout)

Expected outputs:
- `log_path`
- `meas_path`
- `step_count`
- `resolved_step`
- `measures`
- `warnings`

Notes:
For stepped simulations, QPOST emits one-based step ordinals in `.meas` rows.
The service normalizes those back to zero-based step indices so the measure and
waveform surfaces use the same step-selection model.

## describe_qux_export_support

Purpose:
Report whether the companion `QUX.exe` executable is available next to the
configured `QSPICE64.exe` installation and which documented export switches are
usable.

Typical inputs:
- none

Expected outputs:
- `available`
- `qspice_executable`
- `qux_path`
- `supports_export`
- `supports_netlist`
- `supports_dll_variables`
- `supported_switches`
- `supported_export_formats`
- `waveform_input_suffixes`
- `schematic_input_suffixes`
- `notes`

Notes:
This is a read-only capability probe. It does not run an export itself; it is
the discovery-oriented companion for the QUX-backed artifact tools below.

## export_derived_raw

Purpose:
Write one selected step and filtered waveform window from a `.qraw` artifact to
one derived binary raw artifact, or reconstruct all source steps when
`all_steps` is requested.

Typical inputs:
- `raw_path`
- `signals` (one or more source trace names)
- `output_path` (optional)
- `step` or `step_filters` (optional single-step selection)
- `all_steps` (optional boolean; reconstruct all source steps and emit a sibling derived `.log`)
- `component` (optional waveform projection such as `real`, `magnitude`, or `phase`)
- `t_start` and `t_end` (optional axis window)

Expected outputs:
- `raw_path`
- `output_path`
- `plot_name`
- `axis_name`
- `axis_trace_name`
- `step`
- `step_count`
- `point_count`
- `resolved_steps`
- `signal_names`
- `trace_names`
- `components`
- `output_log_path`
- `warnings`

Notes:
By default this tool still emits one selected step. When `all_steps=true`, the
current clean-room stepped path reconstructs time/frequency exports for
`export_derived_raw` only and stages a sibling `.log` with parseable `.step`
lines so later `list_steps` or step-filtered waveform reads can address the
derived artifact. When `component=auto` and the selected source signal is a
complex frequency-domain trace, the export now preserves the native complex
waveform instead of collapsing it to magnitude first. When `output_path` is
omitted, the tool stages a sidecar artifact ending in `-derived.qraw`. If the
source raw does not expose a dedicated axis trace, the exported file uses a
synthetic sample-index time axis.

## merge_waveforms

Purpose:
Merge multiple filtered waveform selections into one derived binary raw
artifact with a shared axis, with optional stepped reconstruction.

Typical inputs:
- `inputs` where each item provides `raw_path` and `signal`
- per-input optional `label`
- per-input optional `step` or `step_filters`
- per-input optional `component`
- per-input optional `t_start` and `t_end`
- `all_steps` (optional)
- `output_path` (optional)

Expected outputs:
- `source_raw_paths`
- `output_path`
- `plot_name`
- `axis_name`
- `axis_trace_name`
- `step`
- `step_count`
- `resolved_steps`
- `output_log_path`
- `point_count`
- `input_count`
- `signal_names`
- `trace_names`
- `components`
- `warnings`

Notes:
All selected inputs must resolve to the same axis after filtering. When
`all_steps=true`, each input must expose the same available step indices and
per-input `step` or `step_filters` selectors are rejected.
When a label is omitted, the merged trace name is derived from the source raw
stem plus the selected signal or component projection. When a selected input is
a complex frequency-domain trace and `component=auto`, the merged artifact now
preserves the native complex trace instead of forcing magnitude projection. The
default output name is a sidecar artifact ending in `-merged.qraw`. Stepped
merges also stage a sibling `.log` file so `list_steps` can recover the merged
step metadata without requiring an optional backend.

## export_waveform_csv

Purpose:
Export one or more waveform expressions from a `.qraw` artifact through the
documented `QUX.exe -Export ... CSV` path.

Typical inputs:
- `raw_path`
- `expressions` (one or more QUX expression strings)
- `point_count` (optional)
- `output_path` (optional)

Expected outputs:
- `raw_path`
- `qux_path`
- `output_path`
- `format`
- `expressions`
- `point_count`
- `line_count`
- `command`

Notes:
Expressions are passed to QUX as-is, so callers should use signal text that
the local QUX build accepts. When `output_path` is omitted, the tool stages a
sidecar CSV artifact ending in `-export.csv`.

## export_waveform_ascii

Purpose:
Export one or more waveform expressions from a `.qraw` artifact through the
documented `QUX.exe -Export ... ASCII` path.

Typical inputs:
- `raw_path`
- `expressions` (one or more QUX expression strings)
- `point_count` (optional)
- `output_path` (optional)

Expected outputs:
- `raw_path`
- `qux_path`
- `output_path`
- `format`
- `expressions`
- `point_count`
- `line_count`
- `command`

Notes:
Expressions are passed to QUX as-is, so callers should use signal text that
the local QUX build accepts. When `output_path` is omitted, the tool stages a
sidecar text artifact ending in `-export.ascii.txt`.

## export_waveform_spice

Purpose:
Export one or more waveform expressions from a `.qraw` artifact through the
documented `QUX.exe -Export ... SPICE` path.

Typical inputs:
- `raw_path`
- `expressions`
- `point_count` (optional)
- `output_path` (optional)

Expected outputs:
- `raw_path`
- `qux_path`
- `output_path`
- `format`
- `expressions`
- `point_count`
- `line_count`
- `command`

Notes:
This is the same execution surface as `export_waveform_ascii`, but it requests
the SPICE-oriented export format and defaults to a `-export.spice.txt` sidecar.

## export_touchstone_s2p

Purpose:
Export waveform expressions through the documented `QUX.exe -Export ... S2P`
path and persist the result as a Touchstone `.s2p` artifact.

Typical inputs:
- `raw_path`
- `expressions`
- `point_count` (optional)
- `output_path` (optional)

Expected outputs:
- `raw_path`
- `qux_path`
- `output_path`
- `format`
- `expressions`
- `point_count`
- `line_count`
- `command`

Notes:
This tool assumes the provided expressions make sense for QUX's S-parameter
export flow. It does not infer port mappings automatically.

## generate_dll_variables

Purpose:
Generate `.DLL` variable declarations from a schematic through the documented
`QUX.exe -DLLvariables` command.

Typical inputs:
- `schematic_path`
- `output_path` (optional)

Expected outputs:
- `schematic_path`
- `qux_path`
- `output_path`
- `line_count`
- `command`

Notes:
This is scaffolding support, not a promise that MCP will compile, link, or load
custom device DLLs on the caller's behalf.

## prepare_bode_analysis

Purpose:
Stage a schematic or netlist with one documented `.bode` directive so the
result can be simulated as a dedicated closed-loop SMPS Bode-analysis artifact.

Typical inputs:
- `source_path`
- `perturbation_source`
- `settling_time`
- `start_frequency`
- `stop_frequency`
- `injection_amplitude`
- `square_periods` (optional)
- `debug` (optional)
- `skip_bias_point` (optional)
- `use_initial_conditions` (optional)
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

Notes:
The frequency and time parameters are accepted as strings so the caller can use
QSpice-friendly engineering suffixes such as `5m`, `1k`, or `1Meg` without the
server reformatting them. For `.qsch` sources the tool stages a schematic copy
with the added directive; for `.net` and `.cir` sources it appends the
directive to the staged netlist artifact.

## prepare_ac

Purpose:
Stage a schematic or netlist with one documented `.ac` directive so the result
can be simulated as a dedicated AC analysis artifact.

Typical inputs:
- `source_path`
- `sweep_type` (`dec`, `oct`, or `lin`)
- `points`
- `start`
- `stop`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

Notes:
Frequency parameters are accepted as strings so the caller can use QSpice-friendly
engineering suffixes such as `1`, `1k`, or `1Meg` without server-side reformatting.

## prepare_dc_sweep

Purpose:
Stage a schematic or netlist with one documented `.dc` directive so the result
can be simulated as a dedicated DC sweep artifact.

Typical inputs:
- `source_path`
- `source` (independent source or element name to sweep)
- `start`
- `stop`
- `step`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

Notes:
Sweep parameters are accepted as strings so the caller can use QSpice-friendly
engineering suffixes without server-side reformatting.

## prepare_loop_gain_analysis

Purpose:
Stage a schematic or netlist with one documented `.ac` directive plus
method-specific loop-gain guidance for Tian or Middlebrook small-signal analysis.

Typical inputs:
- `source_path`
- `method` (`tian` or `middlebrook`)
- `sweep_type` (`dec`, `oct`, or `lin`)
- `points`
- `start`
- `stop`
- `expected_loop_gain_signal` (optional, defaults to `OpenLoopGain`)
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `method`
- `instruction`
- `reference_example`
- `method_notes`
- `expected_loop_gain_signal`
- `warnings`

Notes:
The circuit must already include the probe infrastructure for the chosen method
(see QSpice Examples/Tian.qsch or Examples/MiddleBrook.qsch). For switched-mode
power supplies prefer `prepare_bode_analysis` (`.bode`) instead of small-signal
`.ac` loop gain. After simulation, pass the loop-gain trace to
`measure_stability_margins` or `measure_bode_response`.

## prepare_noise

Purpose:
Stage a schematic or netlist with one documented `.noise` directive.

Typical inputs:
- `source_path`
- `output_node`
- `input_source`
- `sweep_type` (`dec`, `oct`, or `lin`)
- `points`
- `start`
- `stop`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

## prepare_transfer_function

Purpose:
Stage a schematic or netlist with one documented `.tf` directive.

Typical inputs:
- `source_path`
- `output_node`
- `input_source`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

## prepare_sensitivity

Purpose:
Stage a schematic or netlist with one documented `.sens` directive.

Typical inputs:
- `source_path`
- `analysis_type` (`dc` or `ac`)
- `output_node`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

## prepare_temperature_sweep

Purpose:
Stage a schematic or netlist with one documented `.step temp` temperature sweep.

Typical inputs:
- `source_path`
- `start`
- `stop`
- `step`
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

## prepare_transient

Purpose:
Stage a schematic or netlist with one documented `.tran` directive so the
result can be simulated as a dedicated transient-analysis artifact.

Typical inputs:
- `source_path`
- `step`
- `stop`
- `start` (optional)
- `max_step` (optional)
- `use_initial_conditions` (optional)
- `skip_bias_point` (optional)
- `output_path` (optional)

Expected outputs:
- `source_path`
- `output_path`
- `source_kind`
- `instruction`
- `warnings`

Notes:
Time parameters are accepted as strings so the caller can use QSpice-friendly
engineering suffixes such as `1u`, `5m`, or `10m` without server-side reformatting.

The default `output_path` is a sibling such as `{stem}-tran.qsch`. That file is a
**derived snapshot** of `source_path` plus one `.tran` text item — it does not
auto-sync when the source schematic is edited later (including GUI moves). Edit
layout on `source_path` only; re-run this tool after placement changes; simulate
`output_path` but do not open the staged file in the GUI for placement.

Analysis directives (`.tran`, `.ac`, etc.) are placed **below the lowest
component** on the sheet so they do not overlap long source value strings such as
`PULSE(...)`.

## prepare_monte_carlo

Purpose:
Persist an explicit Monte Carlo plan with sampled parameter and component-value
assignments so the same prepared workload can be inspected, rerun, or
summarized later.

Typical inputs:
- `source_path`
- `parameters` as a mapping like `{ "VIN": { "nominal": 12, "tolerance_pct": 5 } }` (optional when `component_values` is provided)
- `component_values` as a mapping like `{ "R1": { "nominal": 1000, "minimum": 900, "maximum": 1100 } }` or `{ "R2": { "tolerance_pct": 1 } }` for a schematic-resolved per-reference override (optional when `parameters` or `component_presets` is provided)
- `component_presets` as a mapping like `{ "R": { "tolerance_pct": 5 } }` to expand one per-prefix default across matching schematic references (optional when `parameters` or `component_values` is provided)
- `sample_count`
- `seed` (optional)
- `stage_native_mc` (optional; stages an inspectable schematic copy that uses native `mc(...)` expressions)
- `output_path` (optional `.json` plan path)

Expected outputs:
- `source_path`
- `plan_path`
- `output_root`
- `sample_count`
- `seed`
- `distribution`
- `parameters`
- `component_values`
- `samples`
- `native_mc_stage`
- `warnings`

Notes:
The current implementation requires a `.qsch` source. Each target can be
described either by `tolerance_pct` or by explicit `minimum` and `maximum`
bounds. Per-prefix `component_presets` expand through the schematic editor into
explicit reference targets, and per-reference component overrides can omit
`nominal` when the schematic value can be resolved safely. The plan persists
explicit per-sample parameter values and component-reference values as a
repo-owned artifact rather than mutating the source schematic. When
`stage_native_mc` is enabled, the service also stages a schematic copy that
uses native `mc(nominal, fractional_tol)` expressions for inspection; every
natively staged target must still provide `tolerance_pct`.

## prepare_worst_case

Purpose:
Persist an explicit worst-case plan with nominal, one-at-a-time, or full corner
assignments so the same prepared workload can be inspected, rerun, or
summarized later.

Typical inputs:
- `source_path`
- `parameters` as a mapping like `{ "VIN": { "nominal": 12, "tolerance_pct": 5 } }` (optional when `component_values` is provided)
- `component_values` as a mapping like `{ "R1": { "nominal": 1000, "minimum": 900, "maximum": 1100 } }` or `{ "R2": { "tolerance_pct": 1 } }` for a schematic-resolved per-reference override (optional when `parameters` or `component_presets` is provided)
- `component_presets` as a mapping like `{ "R": { "tolerance_pct": 5 } }` to expand one per-prefix default across matching schematic references (optional when `parameters` or `component_values` is provided)
- `mode` as `corners` or `one_at_a_time` (optional)
- `include_nominal` (optional)
- `output_path` (optional `.json` plan path)

Expected outputs:
- `source_path`
- `plan_path`
- `output_root`
- `mode`
- `include_nominal`
- `parameters`
- `component_values`
- `cases`
- `warnings`

Notes:
Worst-case preparation is a repo-owned orchestration contract rather than a
claim of native QSpice worst-case syntax. It reuses the same target authoring
rules as Monte Carlo, including per-prefix preset expansion and schematic-based
nominal resolution for per-reference overrides, caps full-corner expansion to a
bounded case count, and persists explicit cases for later inspection.

## run_monte_carlo

Purpose:
Execute one previously prepared Monte Carlo plan through the existing
copy-on-write schematic batch runner.

Typical inputs:
- `prepared_path`
- `output_dir` (optional)
- `parallelism` (optional)
- `dry_run` (optional)
- `timeout_s` (optional)
- `ascii_raw` (optional)
- `extra_switches` (optional)
- `resume` (optional; reuses successful runs from a matching retained manifest in `output_dir`)
- `retained_artifact_policy` (optional; choose whether stale retry and orphaned run directories are cleaned or preserved during resume)

Expected outputs:
- standard persisted batch fields such as `output_root`, `run_count`, `runs`, and `status`
- `sweep_kind` with value `monte_carlo`
- `parameter_names`
- `plan_path`
- `seed`

Notes:
The prepared plan owns the sampled assignments; execution stages one edited
schematic artifact per sample and then reuses the normal netlist-generation and
simulation path. When `resume` is enabled and the output directory already
contains a matching batch manifest, only successful runs with intact retained
artifacts are reused; stale retained run directories and orphaned run
directories are either cleaned or preserved according to
`retained_artifact_policy`, and missing-artifact runs are retried.

## run_worst_case

Purpose:
Execute one previously prepared worst-case plan through the existing
copy-on-write schematic batch runner.

Typical inputs:
- `prepared_path`
- `output_dir` (optional)
- `parallelism` (optional)
- `dry_run` (optional)
- `timeout_s` (optional)
- `ascii_raw` (optional)
- `extra_switches` (optional)
- `resume` (optional; reuses successful runs from a matching retained manifest in `output_dir`)
- `retained_artifact_policy` (optional; choose whether stale retry and orphaned run directories are cleaned or preserved during resume)

Expected outputs:
- standard persisted batch fields such as `output_root`, `run_count`, `runs`, and `status`
- `sweep_kind` with value `worst_case`
- `parameter_names`
- `plan_path`

Notes:
The prepared plan owns the explicit corner assignments; execution stages one
edited schematic artifact per case and then reuses the normal netlist-generation
and simulation path. When `resume` is enabled and the output directory already
contains a matching batch manifest, only successful runs with intact retained
artifacts are reused; stale retained run directories and orphaned run
directories are either cleaned or preserved according to
`retained_artifact_policy`, and missing-artifact runs are retried.

## summarize_tolerance_analysis

Purpose:
Summarize one Monte Carlo or worst-case batch by combining the prepared target
ranges with aggregated numeric single-row `.meas` results across successful
runs.

Typical inputs:
- `batch_path`
- `measures` (optional list to restrict aggregation)
- `refresh_measures` (optional)

Expected outputs:
- `batch_path`
- `plan_path`
- `source_path`
- `output_root`
- `sweep_kind`
- `seed`
- `status`
- `run_count`
- `completed_run_count`
- `successful_run_count`
- `failed_run_count`
- `pending_run_count`
- `completion_pct`
- `measure_coverage_run_count`
- `missing_measure_run_count`
- `measure_coverage_pct`
- `parameter_summaries`
- `component_value_summaries`
- `measure_summaries`
- `warnings`

Notes:
This first slice intentionally aggregates only numeric single-row measurement
outputs so it can reuse the existing QPOST-backed measurement reader. Missing,
non-numeric, or multi-row measures are reported as warnings and skipped. For
worst-case batches `seed` is `null` because the prepared plan is deterministic
rather than sampled. Partial batches now report explicit pending-run and
measure-coverage counts, and parameter/component summaries include observed
coverage for the completed subset in addition to the full prepared target
distribution.

## list_plot_suggestions

Purpose:
Inspect a netlist-oriented source and surface documented `.plot`, `.print`,
`.probe`, and `.abscissa` directives as suggestion-oriented metadata.

Typical inputs:
- `source_path`
- `netlist_output_path` (optional, used when a `.qsch` source must first be staged to a netlist)

Expected outputs:
- `source_path`
- `netlist_path`
- `source_kind`
- `abscissa_expression`
- `suggestions`
- `warnings`

Notes:
This tool does not mutate schematics to add plotting directives. It is meant to
help agents discover existing visualization intent before choosing whether to
read, plot, or further transform the circuit.

## measure_bode_response

Purpose:
Sample magnitude and phase at requested frequencies from one frequency-domain
waveform trace.

Typical inputs:
- `raw_path`
- `signal`
- `frequencies_hz`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)

Expected outputs:
- `raw_path`
- `plot_name`
- `axis_name`
- `signal`
- `step`
- `sample_count`
- `interpolation`
- `samples`

Notes:
This tool requires a frequency-domain `.qraw` artifact with a frequency axis.
When all frequencies are positive, interpolation is performed in log-frequency
space so the result matches Bode-style expectations across decades.

## measure_stability_margins

Purpose:
Compute gain crossover frequency, phase margin, phase crossover frequency, and
gain margin from one loop-gain frequency-domain waveform trace.

Typical inputs:
- `raw_path`
- `signal`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)

Expected outputs:
- `raw_path`
- `plot_name`
- `axis_name`
- `signal`
- `step`
- `sample_count`
- `gain_crossover_hz`
- `phase_margin_deg`
- `phase_crossover_hz`
- `gain_margin_db`
- `stable_at_unity`

Notes:
Requires a frequency-domain `.qraw` artifact with a frequency axis (typically
produced by `.ac`, `.bode`, or loop-gain post-processing). Crossings are
interpolated in log-frequency space when all axis samples are positive.
Margin fields are `null` when the corresponding crossover cannot be found in
the swept range.

## measure_step_response

Purpose:
Compute rise time, delay, overshoot, and settling time from one transient
waveform trace.

Typical inputs:
- `raw_path`
- `signal`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `t_start`, `t_end` (optional axis window)
- `initial_value`, `final_value` (optional; auto-estimated from window edges)
- `lower_pct`, `upper_pct` (rise thresholds, default 10 and 90)
- `settling_band_pct` (default 2)

Expected outputs:
- `raw_path`, `plot_name`, `axis_name`, `signal`, `step`, `sample_count`
- `x_unit`, `y_unit`
- `initial_value`, `final_value`, `peak_value`
- `rise_time_s`, `delay_time_s`, `overshoot_pct`, `settling_time_s`

Notes:
Requires a transient `.qraw` with a time axis. Metric fields are `null` when
the corresponding threshold crossing or settling band cannot be resolved.

## measure_efficiency

Purpose:
Compute average input power, average output power, and Pout/Pin efficiency from
two transient power traces (for example SAVEPOWERS `p(...)` signals).

Typical inputs:
- `raw_path`
- `input_power_signal`
- `output_power_signal`
- `step`, `step_filters` (optional)
- `t_start`, `t_end` (optional averaging window)

Expected outputs:
- `raw_path`, `plot_name`, `input_power_signal`, `output_power_signal`
- `step`, `sample_count`, `t_start`, `t_end`
- `average_input_power_w`, `average_output_power_w`, `efficiency`

Notes:
Requires a transient `.qraw` with a time axis. `efficiency` is `null` when
average input power is zero. Power traces are averaged using absolute values.

## compute_thd

Purpose:
Estimate total harmonic distortion from one time-domain waveform over a trailing
integer-cycle window.

Typical inputs:
- `raw_path`
- `signal`
- `fundamental_hz`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `periods` (optional, defaults to a trailing integer-cycle window)
- `harmonics` (optional)
- `t_end` (optional explicit window end)
- `samples_per_cycle` (optional)

Expected outputs:
- `raw_path`
- `plot_name`
- `signal`
- `step`
- `component`
- `sample_count`
- `window_start_s`
- `window_end_s`
- `fundamental_hz`
- `harmonics`
- `fundamental_amplitude`
- `fundamental_rms`
- `thd_ratio`
- `thd_percent`
- `contributions`

Notes:
This is a derived numeric analysis over waveform samples, not a direct wrapper
around QPOST or a `.four` parsing surface. The service intentionally uses a
trailing integer-cycle window so THD estimates are stable and explicit.

## export_fft_spectrum

Purpose:
Resample one time-domain waveform window and export its single-sided FFT
spectrum as a CSV artifact.

Typical inputs:
- `raw_path`
- `signal`
- `step` (optional)
- `step_filters` (optional mapping such as `{ "vin": 12 }`)
- `component` (optional: `auto`, `real`, `imag`, `magnitude`, `phase`)
- `t_start` and `t_end` (optional)
- `sample_count` (optional)
- `max_frequency_hz` (optional)
- `output_path` (optional)

Expected outputs:
- `raw_path`
- `output_path`
- `signal`
- `step`
- `component`
- `sample_count`
- `bin_count`
- `frequency_resolution_hz`
- `window_start_s`
- `window_end_s`
- `max_frequency_hz`

Notes:
The exported CSV currently contains `frequency_hz`, `amplitude`,
`magnitude_db`, and `phase_deg` columns. This tool requires time-domain data;
it does not reinterpret already frequency-domain traces.

## What Is Intentionally Not A Tool

The following are intentionally outside the planned public surface:

- Arbitrary MATLAB-style or Python-style code evaluation
- Returning complete raw waveform dumps without budgeting
- Treating netlist editing as the default user workflow
- Exposing QSpice subprocess details directly through MCP

## Future Extension Points

Possible post-`v0.1.0` additions include:

- A safe derived-netlist edit tool for narrow expert workflows
- Long-running simulation cancellation if the server adopts asynchronous runs
- Read-only resources documenting supported analyses, artifact conventions, and budget behavior