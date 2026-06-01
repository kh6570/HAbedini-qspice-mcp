"""Tests for the thin subprocess wrapper."""

from __future__ import annotations

import sys
from pathlib import Path

from qspice_mcp.infra.subprocess import run_subprocess


def test_run_subprocess_captures_stdout() -> None:
    result = run_subprocess(
        (sys.executable, "-c", "print('hello from subprocess')"),
        cwd=Path.cwd(),
    )

    assert result.exit_code == 0
    assert "hello from subprocess" in result.stdout
