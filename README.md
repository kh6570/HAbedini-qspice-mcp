# QSpice MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server for the [QSpice](https://www.qorvo.com/design-hub/design-tools/interactive/qspice) circuit simulator. AI assistants use it to inspect and edit `.qsch` schematics, run simulations, read waveforms, and export results through stable JSON tools.

## Installation

**Requirements:** Windows, Python **≥ 3.11** (tested on 3.11 and 3.12), and QSpice (`QSPICE64.exe`).

```bash
git clone https://github.com/kh6570/HAbedini-qspice-mcp.git
cd HAbedini-qspice-mcp
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -e .
cp .env.example .env   # set QSPICE_EXE to QSPICE64.exe
qspice-mcp --describe   # sanity check
```

Optional extras: `[backends]` (richer schematic/raw integration), `[telemetry]` (OpenTelemetry spans), `[dev]` (lint/test tooling).

Configure your MCP client to spawn `qspice-mcp` with `QSPICE_EXE` set, then ask the AI to call `describe_server_capabilities`. Full client setup and workflows are in the [User guide](docs/user-guide.md).

**AI / first-time MCP setup (Cursor or VS Code):** see **[AGENTS.md](AGENTS.md)** — run `scripts/setup_mcp.ps1` to register **user-level** MCP (`%USERPROFILE%\.cursor\mcp.json` / VS Code user `mcp.json`), restart the IDE, verify with `scripts/verify_mcp.ps1`.

**Buck example:** `list_workflow_instructions` → Track A `buck-converter-cpp` or Track B `buck-converter-cpp-catalog` via `read_workflow_instruction`.

## Documentation

**Start here:** **[User guide](docs/user-guide.md)** — client setup, workflows, and troubleshooting (install is above).

| Doc | Purpose |
| --- | --- |
| [User guide](docs/user-guide.md) | Complete usage documentation |
| [Tool reference](docs/tool_reference.md) | MCP tool contracts |
| [Architecture](docs/architecture.md) | Layered design and principles |
| [Error codes](docs/errors.md) | Stable client error codes |
| [Security](docs/security.md) | Threat model |
| [C-Block build guide](docs/cblock_build_guide.md) | Compile DLL custom devices |
| [Changelog](CHANGELOG.md) | Release history |

## License

MIT
