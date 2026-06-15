#!/usr/bin/env python3
"""Probe MCP cold start: stdio ``initialize`` + ``tools/list`` within a time budget."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DEFAULT_BUDGET_S = 30.0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "budget_s",
        nargs="?",
        type=float,
        default=DEFAULT_BUDGET_S,
        help=f"Maximum seconds to wait for tools/list (default: {DEFAULT_BUDGET_S:g}).",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=Path(sys.executable),
        help="Python interpreter that can run ``python -m qspice_mcp`` (default: sys.executable).",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Workspace directory for the MCP server (default: temporary directory).",
    )
    return parser.parse_args(argv)


def _tools_list_response_seen(line: bytes) -> bool:
    return b'"id": 2' in line or b'"id":2' in line


def probe_cold_start(
    *,
    python: Path,
    workspace_root: Path,
    budget_s: float,
) -> float:
    """Run initialize + tools/list and return elapsed seconds."""
    env = os.environ.copy()
    env.setdefault("QSPICE_LOG_LEVEL", "error")
    env.setdefault("QSPICE_DEV_WATCH", "0")
    command = [
        str(python),
        "-u",
        "-m",
        "qspice_mcp",
        "--workspace-root",
        str(workspace_root),
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

    stderr_chunks: list[bytes] = []
    while time.perf_counter() - t0 < budget_s:
        line = proc.stdout.readline()
        if not line:
            break
        if _tools_list_response_seen(line):
            elapsed = time.perf_counter() - t0
            proc.terminate()
            proc.wait(timeout=5)
            return elapsed
        if proc.stderr is not None and proc.poll() is not None:
            stderr_chunks.append(proc.stderr.read())

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    if proc.stderr is not None:
        stderr_chunks.append(proc.stderr.read())
    detail = b"".join(stderr_chunks).decode("utf-8", errors="replace").strip()
    if detail:
        print(detail, file=sys.stderr)
    msg = f"tools/list did not complete within {budget_s:g}s budget"
    raise TimeoutError(msg)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    python = args.python.resolve(strict=False)
    if not python.is_file():
        print(f"Python interpreter not found: {python}", file=sys.stderr)
        return 1

    temp_workspace: tempfile.TemporaryDirectory[str] | None = None
    workspace_root = args.workspace_root
    if workspace_root is None:
        temp_workspace = tempfile.TemporaryDirectory(prefix="qspice-mcp-coldstart-")
        workspace_root = Path(temp_workspace.name)
    else:
        workspace_root = workspace_root.resolve(strict=False)
        workspace_root.mkdir(parents=True, exist_ok=True)

    try:
        elapsed = probe_cold_start(
            python=python,
            workspace_root=workspace_root,
            budget_s=args.budget_s,
        )
    except TimeoutError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"MCP cold-start probe failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if temp_workspace is not None:
            temp_workspace.cleanup()

    print(f"tools/list OK in {elapsed:.2f}s (budget {args.budget_s:g}s)")
    if elapsed >= args.budget_s:
        print("Exceeded cold-start budget.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
