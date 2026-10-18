In the name of God, the Most Gracious, the Most Merciful

# Agent guide — first-time MCP setup (Windows)

Use this file when the user asks to **install, configure, or connect** the QSpice MCP server in **ChatGPT desktop**, **Cursor**, or **VS Code** after cloning this repo.

MCP is registered at **user level** (available in every project). The setup script merges a `qspice` entry into existing configs without removing other servers.

| Client | User config path (Windows) |
|--------|----------------------------|
| **Cursor** | `%USERPROFILE%\.cursor\mcp.json` |
| **VS Code** | `%APPDATA%\Code\User\mcp.json` |
| **ChatGPT desktop** | `%USERPROFILE%\.codex\config.toml` (or `%CODEX_HOME%\config.toml` when set) |

---

## Quick setup (preferred)

From the **cloned repo root** in PowerShell:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1 -WorkspaceRoot "D:\path\to\your\circuit\folder"
```

- Omit `-WorkspaceRoot` → defaults to `%USERPROFILE%\Desktop\qspice-mcp-test`
- Omit `-QspiceExe` → auto-detect `QSPICE64.exe`
- `-Clients Cursor` | `VSCode` | `Both` (default: `Both`)
- For **ChatGPT desktop**, use `-Clients ChatGPT`. This registers `[mcp_servers.qspice]` in the app's shared Codex configuration, preserving other servers, settings, and comments. The Codex CLI is not required.
- Use **Settings → Agent environment → Windows native** and restart the app. This Windows setup writes a `D:\...\python.exe` or `C:\...\python.exe` command, which a WSL agent cannot launch directly. The PowerShell verification checks the server from Windows; confirm the app connection separately with `/mcp`.

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1 -Clients ChatGPT -QspiceExe "D:\Program Files\QSPICE\QSPICE64.exe"
```

For ChatGPT desktop, restart the app, open **Settings → MCP servers**, and check `qspice`; use `/mcp` in the composer to inspect connected servers. Verify the saved configuration with:

```powershell
pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1 -Clients ChatGPT
```

This is the local desktop MCP connection documented in [OpenAI's MCP guide](https://learn.chatgpt.com/docs/extend/mcp), shared with Codex CLI and the IDE extension. Hosted Chat/Work chats can have different tool availability; confirm the connection in the intended desktop chat.

For Cursor or VS Code, tell the user:

1. **Fully restart** Cursor or VS Code (reload is often not enough after first MCP install).
2. Open **Settings → Tools & MCP** and confirm `qspice` is connected.
3. Optional: `pwsh -ExecutionPolicy Bypass -File .\scripts\verify_mcp.ps1`

**Smoke prompt:**

```text
Call describe_server_capabilities on the qspice MCP server and summarize tool groups.
```

---

## What the setup script does

1. Creates `.venv` in the **cloned repo** and runs `pip install -e .`. That clones `mcp-app-core` from GitHub, or uses a checkout of it next to this repository when one is already there.
2. Detects `QSPICE64.exe` (or uses `-QspiceExe`)
3. Merges `qspice` into **user-level** MCP JSON, or TOML for ChatGPT desktop (absolute paths; preserves other servers)
4. Runs `python -m qspice_mcp --describe` as a sanity check

**Important:** The venv stays in the repo you cloned; user-level MCP points at that venv with absolute paths. Re-run setup after moving the repo.

**Simulation workspace** (`--workspace-root`) is where `.qsch` files live — independent of which IDE folder is open.

---

## Agent checklist

| Step | Action |
|------|--------|
| 1 | Confirm Windows + Python ≥ 3.11 on PATH. `pip install` clones `mcp-app-core`; no separate core checkout is required |
| 2 | Run `scripts/setup_mcp.ps1` with user's circuit folder as `-WorkspaceRoot`; use `-Clients ChatGPT` for the desktop app |
| 3 | On failure: install QSpice, pass `-QspiceExe`, or recreate repo `.venv` |
| 4 | Ask user to **fully restart** the selected app or IDE |
| 5 | Call `describe_server_capabilities` via MCP |

---

## MCP config templates (manual repair)

### ChatGPT desktop — `%USERPROFILE%\.codex\config.toml`

Use `%CODEX_HOME%\config.toml` instead if `CODEX_HOME` is set. Merge this table into the existing file; retain other settings and servers. TOML literal strings keep Windows backslashes unchanged. Replace paths with your actual absolute paths.

```toml
[mcp_servers.qspice]
command = 'D:\path\to\qspice-mcp\.venv\Scripts\python.exe'
args = ['-u', '-m', 'qspice_mcp', '--workspace-root', 'D:\circuits', '--log-level', 'error']
startup_timeout_sec = 30
tool_timeout_sec = 180

[mcp_servers.qspice.env]
QSPICE_EXE = 'D:\Program Files\QSPICE\QSPICE64.exe'
QSPICE_LOG_LEVEL = 'error'
QSPICE_DEV_WATCH = '0'
```

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
| ChatGPT lists `qspice` as enabled but has no tools; logs report `No such file or directory (os error 2)` | Check Settings → Agent environment. For this Windows setup, select **Windows native**, restart the app, and start a new local chat. A WSL agent needs a separate launcher; Windows PowerShell verification alone does not check that environment. |
| ChatGPT desktop does not list `qspice` | Run setup with `-Clients ChatGPT`, check the active `CODEX_HOME`, restart the app, then inspect Settings → MCP servers or `/mcp`. Cursor/VS Code JSON configs do not register the server in ChatGPT. |
| `connected=false` immediately | User-level config needs **absolute** `command`; prefer `python.exe` + `["-u","-m","qspice_mcp",…]` over `qspice-mcp.exe`; kill stale `python`/`qspice-mcp` children; **full IDE restart** (not reload). See [user-guide § MCP connected=false](docs/user-guide.md#mcp-shows-connectedfalse). |
| MCP missing in other projects | Re-run setup; config must be in user profile paths above, not repo `.cursor/` |
| MCP loading > 30s | `QSPICE_DEV_WATCH=0` and `--log-level error` (set by setup script) |
| Tools work but sim fails | Check `QSPICE_EXE` and `--workspace-root` folder |
| Moved cloned repo | Re-run `setup_mcp.ps1` to refresh absolute venv path (stale editable-install / `.pth` metadata) |
| Verify outside IDE | `pwsh -File scripts/verify_mcp.ps1` from repo root |

More detail: [docs/user-guide.md](docs/user-guide.md)

---

## Development (contributors)

Repo-local `.cursor/` may exist for your machine but is gitignored. Optional dev launcher: `scripts/dev_qspice_mcp.py`.
