#!/usr/bin/env python3
"""Probe MCP cold start: initialize + tools/list within a time budget."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
WORKSPACE = ROOT / "mcp-workspace"
DEFAULT_BUDGET_S = 30.0


def main() -> int:
    if not PYTHON.is_file():
        print("Missing .venv. Run scripts/setup_mcp.ps1 first.", file=sys.stderr)
        return 1

    budget_s = DEFAULT_BUDGET_S
    if len(sys.argv) > 1:
        budget_s = float(sys.argv[1])

    WORKSPACE.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.setdefault("QSPICE_LOG_LEVEL", "error")
    command = [
        str(PYTHON),
        "-u",
        "-m",
        "qspice_mcp",
        "--workspace-root",
        str(WORKSPACE),
        "--log-level",
        "error",
    ]
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "verify", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    for message in messages:
        proc.stdin.write((json.dumps(message) + "\n").encode())
        proc.stdin.flush()

    while time.perf_counter() - t0 < budget_s:
        line = proc.stdout.readline()
        if not line:
            break
        if b'"id": 2' in line or b'"id":2' in line:
            elapsed = time.perf_counter() - t0
            print(f"tools/list OK in {elapsed:.2f}s")
            proc.terminate()
            return 0 if elapsed < budget_s else 2

    proc.terminate()
    print("tools/list did not complete within budget", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
