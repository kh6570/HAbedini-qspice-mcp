# Agent guide — first-time MCP setup (Windows)

Use this file when the user asks to **install, configure, or connect** the QSpice MCP server in **Cursor** or **VS Code** after cloning this repo.

MCP is registered at **user level** (available in every project). The setup script merges a `qspice` entry into existing configs without removing other servers.

| Client | User config path (Windows) |
|--------|----------------------------|
| **Cursor** | `%USERPROFILE%\.cursor\mcp.json` |
| **VS Code** | `%APPDATA%\Code\User\mcp.json` |

---

## Quick setup (preferred)

From the **cloned repo root** in PowerShell:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1 -WorkspaceRoot "D:\path\to\your\circuit\folder"
```

- Omit `-WorkspaceRoot` → defaults to `%USERPROFILE%\Desktop\qspice-mcp-test`
- Omit `-QspiceExe` → auto-detect `QSPICE64.exe`
- `-Clients Cursor` | `VSCode` | `Both` (default: `Both`)

Then tell the user:

1. **Fully restart** Cursor or VS Code (reload is often not enough after first MCP install).
2. Open **Settings → Tools & MCP** and confirm `qspice` is connected.
3. Optional: `pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1`

**Smoke prompt:**

```text
Call describe_server_capabilities on the qspice MCP server and summarize tool groups.
```

---

## What the setup script does

1. Creates `.venv` in the **cloned repo** and runs `pip install -e .`
2. Detects `QSPICE64.exe` (or uses `-QspiceExe`)
3. Merges `qspice` into **user-level** MCP JSON (absolute paths; preserves other servers)
4. Runs `python -m qspice_mcp --describe` as a sanity check

**Important:** The venv stays in the repo you cloned; user-level MCP points at that venv with absolute paths. Re-run setup after moving the repo.

**Simulation workspace** (`--workspace-root`) is where `.qsch` files live — independent of which IDE folder is open.

---

## Agent checklist

| Step | Action |
|------|--------|
| 1 | Confirm Windows + Python ≥ 3.11 on PATH |
| 2 | Run `scripts/setup_mcp.ps1` with user's circuit folder as `-WorkspaceRoot` |
| 3 | On failure: install QSpice, pass `-QspiceExe`, or recreate repo `.venv` |
| 4 | Ask user to **fully restart** IDE |
| 5 | Call `describe_server_capabilities` via MCP |

---

## MCP config templates (manual repair)

Replace placeholders:

- `REPO_ROOT` — absolute path to cloned repo (contains `.venv`)
- `PYTHON_EXE` — `REPO_ROOT\.venv\Scripts\python.exe`
- `SIM_WORKSPACE` — folder for schematics (e.g. `%USERPROFILE%\Desktop\qspice-mcp-test`)
- `QSPICE_EXE` — e.g. `C:\Program Files\QSPICE\QSPICE64.exe`

User-level configs require **absolute paths** (not `${workspaceFolder}`).

### Cursor — `%USERPROFILE%\.cursor\mcp.json`

Root key: `mcpServers`

```json
{
  "mcpServers": {
    "qspice": {
      "type": "stdio",
      "command": "PYTHON_EXE",
      "args": [
        "-u",
        "-m",
        "qspice_mcp",
        "--workspace-root",
        "SIM_WORKSPACE",
        "--log-level",
        "error"
      ],
      "env": {
        "QSPICE_EXE": "QSPICE_EXE",
        "QSPICE_LOG_LEVEL": "error",
        "QSPICE_DEV_WATCH": "0"
      }
    }
  }
}
```

### VS Code — `%APPDATA%\Code\User\mcp.json`

Root key: `servers` (not `mcpServers`). Command Palette: **MCP: Open User Configuration**

```json
{
  "servers": {
    "qspice": {
      "type": "stdio",
      "command": "PYTHON_EXE",
      "args": [
        "-u",
        "-m",
        "qspice_mcp",
        "--workspace-root",
        "SIM_WORKSPACE",
        "--log-level",
        "error"
      ],
      "env": {
        "QSPICE_EXE": "QSPICE_EXE",
        "QSPICE_LOG_LEVEL": "error",
        "QSPICE_DEV_WATCH": "0"
      }
    }
  }
}
```

---

## Troubleshooting

| Symptom | Likely fix |
|---------|------------|
| `connected=false` immediately | User-level config needs absolute `command`; use `python -m qspice_mcp`; full IDE restart |
| MCP missing in other projects | Re-run setup; config must be in user profile paths above, not repo `.cursor/` |
| MCP loading > 30s | `QSPICE_DEV_WATCH=0` and `--log-level error` (set by setup script) |
| Tools work but sim fails | Check `QSPICE_EXE` and `--workspace-root` folder |
| Moved cloned repo | Re-run `setup_mcp.ps1` to refresh absolute venv path |

More detail: [docs/user-guide.md](docs/user-guide.md)

---

## Development (contributors)

Repo-local `.cursor/` may exist for your machine but is gitignored. Optional dev launcher: `scripts/dev_qspice_mcp.py`.
