# In the name of God, the Most Gracious, the Most Merciful
"""Tests for the thin subprocess wrapper."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from qspice_mcp.infra.subprocess import run_subprocess


def test_run_subprocess_captures_stdout() -> None:
    result = run_subprocess(
        (sys.executable, "-c", "print('hello from subprocess')"),
        cwd=Path.cwd(),
    )

    assert result.exit_code == 0
    assert "hello from subprocess" in result.stdout


def test_run_subprocess_kills_a_timed_out_child() -> None:
    with pytest.raises(subprocess.TimeoutExpired):
        run_subprocess(
            (sys.executable, "-c", "import time; time.sleep(30)"),
            cwd=Path.cwd(),
            timeout_s=0.2,
        )
