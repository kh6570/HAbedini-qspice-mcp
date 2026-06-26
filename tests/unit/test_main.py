"""Tests for the package CLI entry point."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

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
