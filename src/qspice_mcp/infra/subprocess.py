"""Thin subprocess helpers for simulator execution."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.infra.child_processes import (
    register_process,
    register_run,
    unregister_process,
    unregister_run,
)

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
    run_id: str | None = None,
) -> SubprocessResult:
    """Run a subprocess and return normalized execution metadata."""

    started_at = time.perf_counter()
    process = subprocess.Popen(  # noqa: S603
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        env=env,
    )
    register_process(process)
    if run_id is not None:
        register_run(run_id, process)
    try:
        stdout, stderr = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        captured_stdout, captured_stderr = process.communicate()
        exc.stdout = captured_stdout  # type: ignore[assignment]
        exc.stderr = captured_stderr  # type: ignore[assignment]
        raise
    finally:
        unregister_process(process.pid)
        if run_id is not None:
            unregister_run(run_id)
    return SubprocessResult(
        command=tuple(command),
        working_directory=cwd,
        exit_code=process.returncode,
        duration_s=time.perf_counter() - started_at,
        stdout=stdout or "",
        stderr=stderr or "",
    )


__all__ = ["SubprocessResult", "run_subprocess"]
