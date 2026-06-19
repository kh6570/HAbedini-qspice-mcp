"""Tests for the package CLI entry point."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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
