"""Tests for the package CLI entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from qspice_mcp.__main__ import build_arg_parser, run_watchdog_mode

REPO_ROOT = Path(__file__).resolve().parents[2]


def _cli_env(**overrides: str) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("QSPICE_ENABLE_SSE", None)
    env.pop("QSPICE_TRANSPORT", None)
    env["QSPICE_PROBE_SKIP_CLI"] = "1"
    env.update(overrides)
    return env


def test_cli_version_flag_prints_package_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "qspice_mcp", "--version"],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert result.returncode == 0
    assert result.stdout.strip().startswith("qspice-mcp ")


def test_cli_setup_flag_prints_readiness_json() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "qspice_mcp", "--setup"],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_cli_env(),
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "ready" in payload
    assert "qspice" in payload
    assert "workspace" in payload
    assert "dll_build_toolchain" in payload


def test_cli_sse_transport_requires_enable_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "qspice_mcp", "--transport", "sse"],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_cli_env(),
    )

    assert result.returncode == 2
    assert "QSPICE_ENABLE_SSE" in result.stderr


def test_watchdog_flags_parse_parent_and_child_pids() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(
        ["--watchdog", "--parent-pid", "123", "--child-pid", "10", "--child-pid", "11"]
    )

    assert args.watchdog is True
    assert args.parent_pid == 123
    assert args.child_pids == [10, 11]


def test_run_watchdog_mode_requires_parent_pid() -> None:
    parser = build_arg_parser()
    args = parser.parse_args(["--watchdog"])

    assert run_watchdog_mode(args) == 2


def test_run_watchdog_mode_reaps_child_when_parent_absent() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--watchdog",
            "--parent-pid",
            "999999998",
            "--child-pid",
            str(child.pid),
            "--watchdog-poll-interval",
            "0.05",
        ]
    )
    try:
        assert run_watchdog_mode(args) == 0
        child.wait(timeout=5.0)
        assert child.poll() is not None
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5.0)
