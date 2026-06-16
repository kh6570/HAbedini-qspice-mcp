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

### VS Code / Cursor

```json
{
  "mcpServers": {
    "qspice": {
      "command": "D:\\path\\to\\qspice-mcp\\.venv\\Scripts\\qspice-mcp.exe",
      "env": {
        "QSPICE_EXE": "C:\\Program Files\\QSPICE\\QSPICE64.exe"
      }
    }
  }
}
```

Use the **full path** to the virtualenv executable on Windows.

**First prompt:**

```text
Call describe_server_capabilities for the qspice MCP server and summarize the available tool groups.
```

### Claude Desktop

Same pattern: `command` = venv `qspice-mcp.exe`, `env.QSPICE_EXE` = QSpice path. Restart Claude after editing `claude_desktop_config.json`.

### Inspector CLI

Let Inspector spawn the server — do not start `qspice-mcp` in the same terminal first.

```powershell
npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/list

npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/call --tool-name describe_server_capabilities
```

Add `-e QSPICE_EXE="C:\Program Files\QSPICE\QSPICE64.exe"` after `inspector` if the variable is not set in your shell.

---

## Quick smoke test

From the repo root (PowerShell):

```powershell
npx -y @modelcontextprotocol/inspector .\.venv\Scripts\qspice-mcp.exe --cli --transport stdio --method tools/call --tool-name materialize_reference_circuit --tool-arg recipe_id="buck_converter_cpp"
```

Then run without `dry_run`, `list_signals` on the `.qraw`, and `read_waveform` with `max_points=200`.

---

## Typical workflow

1. **Inspect** — `inspect_schematic`, `list_components`, `read_component`, or `read_subcircuit`.
2. **Edit** — `set_component_value`, `add_instruction`, `remove_instruction`, symbol/DLL tools as needed. Use `describe_edit_capability` before uncertain edits.
3. **Simulate** — `run_simulation` (cached when netlist and switches match a prior success).
4. **Sweeps / batches** — `run_value_sweep`, `run_param_sweep`, or `submit_batch` + `get_batch_status`.
5. **Waveforms** — `list_signals`, `read_waveform` (bounded), `measure_waveform`, `plot_waveforms`.
6. **Logs / measures** — `read_log`, `read_measures`.
7. **Exports** — QUX CSV/ASCII/S2P, `export_derived_raw`, `merge_waveforms`.
8. **Statistics** — `prepare_monte_carlo` / `run_monte_carlo`, worst-case tools.
9. **Discover** — `describe_server_capabilities` when backends or degraded groups matter.

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

---

## DLL / C-block devices

1. `scaffold_dll_device` or `scaffold_dll_device_from_symbol`
2. Build the DLL with `build_dll_device` or the [C-Block Build Guide](cblock_build_guide.md)
3. Place `.dll` next to the `.qsch`
4. `validate_dll_symbol_signature` before simulating
5. `run_simulation`

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

## Further reference

| Doc | Contents |
| --- | --- |
| [Tool reference](tool_reference.md) | Every MCP tool — inputs, outputs, notes |
| [Error codes](errors.md) | Stable `error_code` values for clients |
| [Security](security.md) | Threat model and sandbox |
| [C-Block build guide](cblock_build_guide.md) | Compile DLL scaffolds |
| [CHANGELOG](../CHANGELOG.md) | Release history |

Bundled recipes: `list_reference_circuit_recipes` / `describe_reference_circuit_recipe` / `materialize_reference_circuit`.
