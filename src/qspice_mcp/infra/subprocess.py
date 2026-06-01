"""Thin subprocess helpers for simulator execution."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SubprocessResult:
    """Completed subprocess metadata captured for diagnostics."""

    command: tuple[str, ...]
    working_directory: Path
    exit_code: int
    duration_s: float
    stdout: str
    stderr: str


def run_subprocess(
    command: tuple[str, ...],
    *,
    cwd: Path,
    timeout_s: float | None = None,
    env: dict[str, str] | None = None,
) -> SubprocessResult:
    """Run a subprocess and return normalized execution metadata."""

    started_at = time.perf_counter()
    completed = subprocess.run(  # noqa: S603
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout_s,
        check=False,
        env=env,
    )
    return SubprocessResult(
        command=tuple(command),
        working_directory=cwd,
        exit_code=completed.returncode,
        duration_s=time.perf_counter() - started_at,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


__all__ = ["SubprocessResult", "run_subprocess"]
