#!/usr/bin/env python3
"""Quick stdio MCP handshake smoke test."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / ".venv" / "Scripts" / "qspice-mcp.exe"
DEV_LAUNCHER = ROOT / "scripts" / "dev_qspice_mcp.py"


def main() -> int:
    env = os.environ.copy()
    env.setdefault("QSPICE_EXE", r"C:\Program Files\QSPICE\QSPICE64.exe")
    env["QSPICE_DEV_WATCH"] = "0"
    use_dev = "--dev" in sys.argv
    command = (
        [sys.executable, str(DEV_LAUNCHER), "--workspace-root", str(ROOT)]
        if use_dev
        else [str(EXE), "--workspace-root", str(ROOT)]
    )
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"},
        },
    }
    out, err = proc.communicate((json.dumps(init) + "\n").encode(), timeout=20)
    print("STDOUT:", out[:800].decode(errors="replace"))
    print("STDERR:", err[:400].decode(errors="replace"))
    print("RC:", proc.returncode)
    return 0 if b'"result"' in out else 1


if __name__ == "__main__":
    raise SystemExit(main())
