# QSpice MCP User Guide

One guide for installing, connecting, and using the QSpice MCP server with AI clients.

---

## What this is

[qspice-mcp](https://github.com/kh6570/HAbedini-qspice-mcp) is a [Model Context Protocol](https://modelcontextprotocol.io) server for the [QSpice](https://www.qorvo.com/design-hub/design-tools/interactive/qspice) simulator on Windows. AI assistants use it to:

- Inspect and edit `.qsch` schematics
- Run simulations and sweeps
- Read waveforms, operating points, and measurements
- Export artifacts and scaffold mixed-signal devices

**Source of truth:** your `.qsch` file. Netlists, logs, and `.qraw` files are derived outputs.

---

## Install

Follow the [Installation steps in the README](../README.md#installation): clone the repo, create a virtualenv, `pip install -e .`, set `QSPICE_EXE`, and verify with `qspice-mcp --describe`. Requirements are Windows, Python ≥ 3.11, and QSpice (`QSPICE64.exe`).

### Optional extras

| Extra | Purpose |
| --- | --- |
| `[backends]` | Richer schematic/raw integration when installed |
| `[telemetry]` | OpenTelemetry span export |
| `[dev]` | Lint, test, and coverage tooling (contributors) |

Base install is enough for MCP usage with the supported clean-room schematic subset and common waveform readback. Call `describe_server_capabilities` to see what is active on your machine.

---

## Connect an MCP client

**Easiest path (AI-assisted):** open **[AGENTS.md](../AGENTS.md)** and run `scripts/setup_mcp.ps1`. That merges `qspice` into **user-level** MCP config (Cursor: `%USERPROFILE%\.cursor\mcp.json`; VS Code: `%APPDATA%\Code\User\mcp.json`) and runs a sanity check. JSON templates are in AGENTS.md.

**First-time order:**

1. Verify `qspice-mcp --describe` works.
2. Configure your client to **spawn** `qspice-mcp` (do not run it manually for normal use).
3. Set `QSPICE_EXE` in the server environment.
4. Restart the client.
5. Ask the AI to call `describe_server_capabilities` before edits or simulations.

### Cursor — `%USERPROFILE%\.cursor\mcp.json`

Root key: `mcpServers`.

```json
{
  "mcpServers": {
    "qspice": {
      "type": "stdio",
      "command": "D:\\path\\to\\qspice-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-u", "-m", "qspice_mcp", "--workspace-root", "C:\\path\\to\\circuits", "--log-level", "error"],
      "env": {
        "QSPICE_EXE": "C:\\Program Files\\QSPICE\\QSPICE64.exe"
      }
    }
  }
}
```

### VS Code — `%APPDATA%\Code\User\mcp.json`

Root key: `servers` (not `mcpServers`). Command Palette: **MCP: Open User Configuration**.

```json
{
  "servers": {
    "qspice": {
      "type": "stdio",
      "command": "D:\\path\\to\\qspice-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-u", "-m", "qspice_mcp", "--workspace-root", "C:\\path\\to\\circuits", "--log-level", "error"],
      "env": {
        "QSPICE_EXE": "C:\\Program Files\\QSPICE\\QSPICE64.exe"
      }
    }
  }
}
```

Use **absolute paths** in user-level configs (placeholders like `${workspaceFolder}` often fail there). Prefer `python.exe -u -m qspice_mcp` over the `qspice-mcp.exe` entry point — it avoids file-lock startup failures on Windows.

**First prompt:**

```text
Call describe_server_capabilities for the qspice MCP server and summarize the available tool groups.
```

### Claude Desktop

Same pattern: `command` = venv `qspice-mcp.exe`, `env.QSPICE_EXE` = QSpice path. Restart Claude after editing `claude_desktop_config.json`.

### One-click `.mcpb` bundle

For MCPB-aware clients (e.g. Claude Desktop **Settings → Extensions**), build a single-file bundle and drag it in:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\build_mcpb.ps1
```

This writes `dist\qspice-mcp.mcpb`. It uses the official `mcpb` CLI when `npx` is available and otherwise falls back to a dependency-free staged zip (pass `-ForceZip` to force the fallback). The bundle uses the MCPB `uv` server type, so the host resolves Python dependencies from `pyproject.toml` at install time — nothing is vendored. On install the client prompts for the **QSPICE64.exe path** and a **simulation workspace** (and optional **session mode**), then wires the server up with no manual JSON editing. `uv` must be available to the host for this server type.

### Inspector CLI

Let Inspector spawn the server — do not start `qspice-mcp` in the same terminal first.

```powershell
npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/list

npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/call --tool-name describe_server_capabilities
```

Add `-e QSPICE_EXE="C:\Program Files\QSPICE\QSPICE64.exe"` after `inspector` if the variable is not set in your shell.

---

## Quick smoke test

From the repo root (PowerShell), materialize a bundled recipe into the workspace:

```powershell
npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/call --tool-name materialize_reference_circuit --tool-arg recipe_id="buck_converter_cpp"
```

Then, through your MCP client (or further `tools/call` invocations):

1. `run_simulation(source_path="Buck-converter.qsch", dry_run=true)` — confirms the planned command without launching QSpice.
2. `run_simulation(source_path="Buck-converter.qsch")` — runs the simulation and reports the `.log`/`.qraw` artifact paths.
3. `list_signals(raw_path="Buck-converter.qraw")` — enumerates the stored traces.
4. `read_waveform(raw_path="Buck-converter.qraw", signal="V(out)", max_points=200)` — bounded waveform readback.

---

## MCP Prompts

The server exposes **MCP Prompts** — slash-command workflow templates that clients
can insert into chat. They are read-only guidance messages; the AI still calls
tools explicitly.

| Prompt | Purpose |
| --- | --- |
| `qspice_buck_converter_from_scratch` | Author a buck converter, netlist, simulate, measure |
| `qspice_debug_convergence` | Diagnose a failed or non-converging simulation from a log |
| `qspice_run_and_measure` | Run a simulation and read bounded waveform measurements |
| `qspice_author_dll_device` | Author a mixed-signal C-block/DLL device (device-spec first, scaffold fallback) |
| `qspice_sweep_design` | Plan and execute a parameter sweep on a schematic |
| `qspice_smps_loop_gain` | Measure SMPS loop gain and stability margins (Bode/.meas fra) |
| `qspice_tolerance_analysis` | Monte Carlo + worst-case tolerance analysis with a summary |

In **Cursor** or **VS Code**, open the MCP prompts picker (when supported) or ask
the assistant to use a prompt by name. Prompt arguments (`vin`, `log_path`,
`schematic_path`, etc.) are filled by the client when invoking the prompt.

Prompts complement bundled **workflow instructions** (`list_workflow_instructions`,
`read_workflow_instruction`) and **recipe resources** (`recipe://{recipe_id}/…`).
Prefer `list_reference_circuit_recipes` before materializing a bundled example.

### MCP Resources

The server also publishes read-only **MCP resources** clients can attach to chat:

| Resource | Contents |
| --- | --- |
| `reference://directives` | QSpice directive quick reference (`.tran`, `.ac`, `.meas`, `.options`, …) |
| `guidelines://qspice-artifacts` | How derived artifacts (`.net`, `.log`, `.qraw`) relate to the `.qsch` |
| `guidelines://qspice-measurements` | Measurement workflow guidance (`.meas`, QPOST, bounded readback) |
| `recipe://{recipe_id}/manifest` and `recipe://{recipe_id}/{document}` | Bundled recipe manifests and catalog documents |
| `workspace-artifact://{path}` | Small text artifacts from the simulation workspace |

`describe_server_capabilities` returns a `guidance` block listing the prompts and
resources active on your install.

---

## Typical workflow

1. **Inspect** — `inspect_schematic`, `list_components`, `read_component`, or `read_subcircuit`.
2. **Edit** — `set_component_value`, `add_instruction`, `remove_instruction`, symbol/DLL tools as needed. Use `describe_edit_capability` before uncertain edits.
3. **Stage analyses** — prefer the typed `prepare_*` tools over hand-written directives: `prepare_transient`, `prepare_ac`, `prepare_dc_sweep`, `prepare_bode_analysis`, `prepare_meas`, `prepare_save`, `prepare_options`, `prepare_noise`, `prepare_four`, `prepare_op`, `prepare_net`, plus statistical `prepare_monte_carlo` / `prepare_worst_case`. They validate arguments and write well-formed directives; `add_instruction` remains the raw fallback.
4. **Simulate** — `run_simulation` (cached when netlist and switches match a prior success).
5. **Sweeps / batches** — `run_value_sweep`, `run_param_sweep`, or `submit_batch` + `get_batch_status`.
6. **Waveforms** — `list_signals`, `read_waveform` (bounded), `measure_waveform`, `plot_waveforms`.
7. **Logs / measures** — `read_log`, `read_measures`.
8. **Exports** — QUX CSV/ASCII/S2P, `export_derived_raw`, `merge_waveforms`.
9. **Statistics** — `run_monte_carlo`, worst-case tools, `summarize_tolerance_analysis`.
10. **Discover** — `describe_server_capabilities` when backends or degraded groups matter.

Full tool list: [Tool reference](tool_reference.md).

---

## Architecture (concepts)

`qspice-mcp` is schematic-first (`.qsch` is the source of truth), returns compact stable JSON instead of raw simulator objects, enforces waveform size budgets, and degrades gracefully when optional `[backends]` are absent. See [Architecture](architecture.md) for the layered design.

---

## Common problems

### MCP shows `connected=false`

Cursor and VS Code mark a server `connected=false` when the MCP child process exits during startup or never completes the MCP handshake (`initialize` + `tools/list`). The fixes below apply to **instant** failures (status flips red within a few seconds), not slow first-time loads.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `connected=false` immediately after adding or editing MCP config | User-level config uses a relative or placeholder `command` (for example `${workspaceFolder}`) | Re-run `scripts/setup_mcp.ps1` from the cloned repo, or set **absolute** paths in `%USERPROFILE%\.cursor\mcp.json` (Cursor) or `%APPDATA%\Code\User\mcp.json` (VS Code). See [AGENTS.md](../AGENTS.md). |
| `connected=false` after a prior session or crash | Stale `python.exe` / `qspice-mcp` child still running or holding a lock on the venv entry point | Close the IDE fully, end orphaned `python` / `qspice-mcp` processes in Task Manager, then restart the IDE. |
| Config looks correct but startup still fails | `command` points at `qspice-mcp.exe` while Windows holds a lock on that file, or at a Python that is not the repo venv | Prefer **`python -u -m qspice_mcp`** as the launch form: absolute path to `.venv\Scripts\python.exe` as `command`, with `-u`, `-m`, `qspice_mcp` in `args` (this is what `setup_mcp.ps1` writes). Avoid bare `qspice-mcp` / `qspice-mcp.exe` in user-level configs. |
| Failure after moving or recloning the repo | Broken editable-install metadata: MCP still points at an old venv or site-packages `.pth` | From the **new** repo root: recreate `.venv`, `pip install -e .`, then re-run `scripts/setup_mcp.ps1` so user-level MCP JSON picks up the new absolute paths. |
| Changed MCP config but status unchanged | IDE reload did not restart MCP subprocesses | **Fully quit** Cursor or VS Code and reopen (Settings → reload is often not enough after the first MCP install). |
| Need to confirm the server boots outside the IDE | — | From the repo root: `pwsh -File scripts/verify_mcp.ps1` (runs `--describe` and a stdio `tools/list` budget probe). |

**Sanity check outside the IDE:**

```powershell
.\.venv\Scripts\python.exe -u -m qspice_mcp --describe --log-level error
.\.venv\Scripts\python.exe scripts\verify_mcp_stdio.py 30
```

Both must exit 0. If they fail in a normal terminal, fix the venv/`QSPICE_EXE` setup before debugging the IDE client.

### Simulation, paths, and stdio misuse

| Problem | Fix |
| --- | --- |
| `QSPICE_EXE` missing | Set to `C:\Program Files\QSPICE\QSPICE64.exe`; re-run `--describe` |
| Tools work but simulation fails | Check `QSPICE_EXE` and the `--workspace-root` folder in MCP config |
| Paths with spaces | Quote values: `QSPICE_EXE="C:\Program Files\QSPICE\QSPICE64.exe"` |
| `Invalid JSON` / stdio error | You typed a shell command into a terminal running `qspice-mcp`; use Ctrl+C and let the **client** spawn the server |
| Missing DLL / C-block errors | [C-Block Build Guide](cblock_build_guide.md) |

### Manual server run (debug only)

```powershell
.\.venv\Scripts\python.exe -u -m qspice_mcp --workspace-root "C:\path\to\circuits" --log-level error
```

That terminal is JSON-RPC only — not a normal shell. Prefer `scripts/verify_mcp.ps1` for a non-interactive health check.

Run `python -m qspice_mcp --setup` to print a JSON readiness report (QSpice
executable, workspace root, and optional DLL build toolchains) without starting
the server.

### CLI flags and environment variables

CLI flags override the matching `QSPICE_*` environment variable (which may come
from your shell, the MCP launcher `env` block, or a local `.env`).

| CLI flag | Environment variable | Purpose |
| --- | --- | --- |
| `--transport` | `QSPICE_TRANSPORT` | Transport (`stdio` default, `sse` experimental) |
| _(none)_ | `QSPICE_ENABLE_SSE` | Must be `true` to allow `--transport sse` |
| `--session-mode` | `QSPICE_SESSION_MODE` | `cold` (default) always cold-launches; `auto` reuses a running live-GUI session first (see [Live-GUI session reuse](#live-gui-session-reuse)) |
| `--qspice-exe` | `QSPICE_EXE` | Path to `QSPICE64.exe` |
| `--workspace-root` | `QSPICE_WORKSPACE_ROOT` | Folder for schematics and derived artifacts |
| `--log-level` | `QSPICE_LOG_LEVEL` | `debug`, `info`, `warning`, or `error` |
| `--log-folder` | `QSPICE_LOG_FOLDER` | Optional folder for rotating server log files |
| `--recipe-path` | `QSPICE_RECIPE_PATH` | Optional override for the recipe catalog directory |

The experimental `sse` transport is gated: `--transport sse` exits with an error
unless `QSPICE_ENABLE_SSE=true` is also set.

---

## Live-GUI session reuse

By default (`session_mode=cold`) every `run_simulation` cold-launches a fresh QSpice
CLI process. With `session_mode=auto` plus a configured live-GUI bridge
(`QSPICE_LIVE_GUI_BRIDGE_COMMAND`), the server will try to reuse an already-running
live-GUI session before cold-launching. Reuse is gated on a session actually being
reachable; if none is running, the bridge is unavailable, or the run times out, the
server **falls back to a normal cold launch**, so behavior is unchanged when no bridge
is present.

To participate in reuse, the external bridge process must implement a `run_netlist`
command on the JSONL command/event protocol that the live-GUI session tools already
use (`bridge.commands.jsonl` / `bridge.events.jsonl`):

- The server appends a command record to `bridge.commands.jsonl`:

```json
{"command_id": 7, "command": "run_netlist", "payload": {"netlist_path": "…/demo.net", "log_path": "…/demo.log", "raw_path": "…/demo.qraw", "extra_switches": []}}
```

- The bridge runs the netlist through the live GUI and then appends one terminal event
  to `bridge.events.jsonl`, echoing the same `command_id`:
  - `{"event": "run_netlist_complete", "command_id": 7, "payload": {…}}` on success, or
  - `{"event": "run_netlist_failed", "command_id": 7, "payload": {"error": "…"}}` on failure.

On `run_netlist_complete` the `run_simulation` result reports
`session_strategy = "reuse_live_gui"` plus `live_gui_session_id`. A
`run_netlist_failed` event surfaces as a simulation error; a timeout or missing session
silently falls back to a cold launch. Bundling such a bridge is out of scope for this
server — only the server side of the contract ships here.

---

## DLL / C-block devices

**Fastest path — one call from a device spec:**

1. `describe_device_spec` — returns the JSON device-spec schema and an example.
2. `create_dll_device_from_spec(spec_path="my_device.json", schematic_path="top.qsch")` — places the `.DLL` block with all pins, scaffolds the C++ source (with the per-instance state idiom), and optionally builds the DLL in one call.

**Step-by-step path (existing block or manual control):**

1. `scaffold_dll_device`, or `scaffold_dll_device_from_symbol` when the block already exists in the schematic
2. Build the DLL with `build_dll_device` or the [C-Block Build Guide](cblock_build_guide.md)
3. Place `.dll` next to the `.qsch`
4. `validate_dll_symbol_signature` before simulating
5. `run_simulation`

**Symbol interop (`.qsym`):** `export_symbol_to_qsym` writes a component's embedded
symbol to a standalone `.qsym` library file, and `add_component_from_qsym` places a
component from one — useful for exchanging symbols with external QSpice symbol
libraries and PinDef-style device generators.

QSpice installs a bundled Digital Mars C++ compiler at `<install>/dm/bin/dmc.exe`.
Set `QSPICE_EXE` in your MCP server environment so `build_dll_device` and
`write_workspace_text_file` can auto-build `.cpp` sources with DMC (no Visual Studio
required for typical QSpice-generated C++98 blocks). Use `toolchain="msvc"` when you
need modern C++.

### `write_workspace_text_file` auto-build

When you write a `.c`/`.cpp`/`.cc`/`.cxx` file, the tool can compile the sibling
`.dll` in the same call (default on; pass `build_dll_after_write=false` to skip).

| Outcome | Response fields | What to do |
| --- | --- | --- |
| Write + compile OK | `output_path`, `dll_build` | Simulate or validate as needed |
| Write OK, compile failed, no `.dll` | `output_path`, `dll_build_error` | Set `QSPICE_EXE`, install MSVC/CMake, or run `build_dll_device` manually — see [C-Block Build Guide](cblock_build_guide.md) |
| Write OK, `.dll` already present | `output_path`, `dll_build` with `skipped_rebuild: true` | Rebuild with `build_dll_device` if the source changed |
| Write + optional validation | `dll_validation` when `schematic_path` and `dll_reference` are both set | Fix pin/export mismatches if the tool raises `ValidationError` |

`dll_toolchain=auto` prefers bundled DMC when `QSPICE_EXE` resolves, then MSVC, then
CMake. IDE-spawned MCP often lacks `cl` on PATH even when Visual Studio is installed;
configure `QSPICE_EXE` or build from a Developer Prompt / explicit `build_dll_device`
call. Full field list: [Tool reference — write_workspace_text_file](tool_reference.md#write_workspace_text_file).

**Buck example — two workflows:**

| Track | Use when | MCP discovery | MCP workflow |
| --- | --- | --- | --- |
| **A — scratch** | Build from empty workspace with authoring tools only | `list_workflow_instructions` | `read_workflow_instruction(instruction_id="buck-converter-cpp")` |
| **B — catalog** | Discover or materialize bundled canonical recipes | `list_reference_circuit_recipes`, `describe_reference_circuit_recipe(recipe_id="buck_converter_cpp")` | `read_workflow_instruction(instruction_id="buck-converter-cpp-catalog")` |

Discover recipes with `list_reference_circuit_recipes` and inspect manifests with `describe_reference_circuit_recipe`. Preflight scratch builds with `describe_topology_authoring_support`.

---

## Optional telemetry

Every tool response includes `trace_id`. OpenTelemetry spans need `[telemetry]`, `QSPICE_TELEMETRY_ENABLED=true`, and a tracer provider configured before `main()` — see `describe_server_capabilities` for readiness.

---

## Agent skills (optional)

The package bundles a small catalog of **agent skills** — client-side `SKILL.md`
guides that teach an AI agent how to drive QSpice well (the core workflow, and
convergence debugging). Skills are loaded by your *agent*, not the MCP server, so
they add no per-request cost to the server and only enter context when a relevant
task triggers them.

They ship inside the package (`qspice_mcp/data/skills/`) and install into your
agent's skills directory:

```powershell
pwsh -File scripts/install_skills.ps1
```

By default this copies each skill into `~/.agents/skills/` (discovered by most
MCP-aware agents). Use `-SkillsRoot <path>` for a different location, `-Groups`
to pick groups (default `qspice-core`), and `-Force` to overwrite. Restart the
agent afterward. Install only the groups you need — agents trigger the right
skill more reliably when fewer are loaded.

---

## Further reference

| Doc | Contents |
| --- | --- |
| [Tool reference](tool_reference.md) | Every MCP tool — inputs, outputs, notes |
| [Error codes](errors.md) | Stable `error_code` values for clients |
| [Security](security.md) | Threat model and sandbox |
| [C-Block build guide](cblock_build_guide.md) | Compile DLL scaffolds |
| [CHANGELOG](../CHANGELOG.md) | Release history |

Bundled recipes: `list_reference_circuit_recipes` / `describe_reference_circuit_recipe` / `materialize_reference_circuit`.

Topology knowledge pack (clean-room DC-DC converter design references): `list_topology_blocks` / `describe_topology_block` / `search_topology_blocks`, plus `validate_topology_contribution` for proposing new data-only blocks. New converters are added as bundled data, not as new tools.
