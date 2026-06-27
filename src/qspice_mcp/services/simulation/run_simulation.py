"""Service for QSpice simulation planning and execution."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from qspice_mcp.adapters import select_adapter
from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.core.exceptions import SimulationError, SimulationTimeoutError
from qspice_mcp.infra.child_processes import consume_run_cancellation
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.simulation_subprocess import run_subprocess_with_log_progress
from qspice_mcp.services._internals.managed_outputs import (
    discard_output_backups,
    prepare_output_backups,
    restore_output_backups,
)
from qspice_mcp.services._internals.simulation_cache import SimulationArtifactCache
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._netlist_includes import (
    collect_netlist_includes,
    hash_include_dependencies,
)

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.adapters.base import QSpiceAdapter, SimulationCommand


@dataclass(frozen=True, slots=True)
class SimulationRun:
    """Resolved simulation command plus optional execution outcome."""

    adapter_key: str
    command: tuple[str, ...]
    working_directory: Path
    netlist_path: Path
    log_path: Path
    raw_path: Path
    dry_run: bool
    started_at: datetime
    exit_code: int | None = None
    duration_s: float | None = None
    stdout: str = ""
    stderr: str = ""
    log_exists: bool = False
    raw_exists: bool = False
    cached: bool = False
    cache_key: str | None = None


SERVICE_SPEC = ServiceSpec(
    name="run_simulation",
    title="Run Simulation",
    summary="Plan or execute a QSpice simulation for a derived .net or .cir file.",
    phase="implemented",
    read_only=False,
    long_running=True,
)


def _build_settings(
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None,
) -> QSpiceSettings:
    """Normalize service settings while preserving the caller's workspace root."""

    if settings is None:
        return QSpiceSettings(workspace_root=workspace_root).normalized()
    return settings.normalized()


def _resolve_output_path(
    raw_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
) -> Path:
    """Resolve an optional output path inside the workspace root."""

    if raw_path is None:
        return default.resolve(strict=False)
    return resolve_workspace_path(raw_path, workspace_root=workspace_root)


def _build_run(
    *,
    adapter_key: str,
    plan: SimulationCommand,
    dry_run: bool,
    exit_code: int | None = None,
    duration_s: float | None = None,
    stdout: str = "",
    stderr: str = "",
    cached: bool = False,
    cache_key: str | None = None,
) -> SimulationRun:
    """Construct a service result from a command plan and optional process result."""

    return SimulationRun(
        adapter_key=adapter_key,
        command=plan.command,
        working_directory=plan.working_directory,
        netlist_path=plan.netlist_file,
        log_path=plan.log_file,
        raw_path=plan.raw_file,
        dry_run=dry_run,
        started_at=datetime.now().astimezone(),
        exit_code=exit_code,
        duration_s=duration_s,
        stdout=stdout,
        stderr=stderr,
        log_exists=plan.log_file.is_file(),
        raw_exists=plan.raw_file.is_file(),
        cached=cached,
        cache_key=cache_key,
    )


def _classify_log_failure(
    *,
    adapter: QSpiceAdapter,
    plan: SimulationCommand,
    process_exit_code: int,
    stderr: str,
    probe_version: str | None = None,
) -> None:
    """Raise a domain error when the adapter finds a decisive log failure signature."""

    if not plan.log_file.is_file():
        return
    try:
        log_text = plan.log_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    error = adapter.classify_simulation_log(
        log_text,
        exit_code=process_exit_code,
        stderr=stderr,
        probe_version=probe_version,
    )
    if error is not None:
        raise error


def _raise_nonzero_exit_error(*, exit_code: int, stderr: str) -> None:
    """Raise the stable domain error for one failed simulator exit."""

    raise SimulationError(
        "QSpice exited with a non-zero status.",
        exit_code=exit_code,
        stderr=stderr,
    )


def run_simulation(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None = None,
    dry_run: bool = False,
    timeout_s: float | None = None,
    log_path: str | Path | None = None,
    raw_output_path: str | Path | None = None,
    extra_switches: tuple[str, ...] = (),
    ascii_raw: bool = False,
    run_id: str | None = None,
) -> SimulationRun:
    """Plan or execute a QSpice run for a derived `.net` or `.cir` file."""

    normalized_workspace = workspace_root.resolve(strict=False)
    effective_settings = _build_settings(workspace_root=normalized_workspace, settings=settings)
    effective_timeout_s = effective_settings.resolve_timeout_s(timeout_s)
    probe = probe_qspice(effective_settings)
    adapter = select_adapter(probe)
    resolved_netlist = validate_existing_file(
        netlist_path,
        workspace_root=normalized_workspace,
        suffixes=(".cir", ".net"),
    )
    resolved_log_path = _resolve_output_path(
        log_path,
        workspace_root=normalized_workspace,
        default=resolved_netlist.with_suffix(".log"),
    )
    resolved_raw_path = _resolve_output_path(
        raw_output_path,
        workspace_root=normalized_workspace,
        default=resolved_netlist.with_suffix(".qraw"),
    )
    plan = adapter.build_simulation_command(
        probe,
        resolved_netlist,
        log_file=resolved_log_path,
        raw_file=resolved_raw_path,
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
    )
    if dry_run:
        return _build_run(adapter_key=adapter.key, plan=plan, dry_run=True)

    cache_root = effective_settings.cache_dir
    if cache_root is None:
        raise AssertionError("Normalized settings must define cache_dir.")
    cache = SimulationArtifactCache(
        cache_root / "simulation",
        max_cache_bytes=effective_settings.max_cache_bytes,
    )
    cache_key = cache.build_key(
        netlist_path=resolved_netlist,
        adapter_key=adapter.key,
        executable=plan.command[0],
        executable_version=probe.version,
        executable_mtime=(
            probe.executable.stat().st_mtime
            if probe.executable is not None and probe.executable.is_file()
            else None
        ),
        extra_switches=extra_switches,
        ascii_raw=ascii_raw,
        include_hashes=hash_include_dependencies(
            collect_netlist_includes(resolved_netlist, workspace_root=normalized_workspace)
        ),
    )
    cached_entry = cache.get(cache_key)
    if cached_entry is not None:
        output_backups = prepare_output_backups((plan.log_file, plan.raw_file), label="cache-hit")
        try:
            cache.materialize(
                cached_entry,
                log_destination=plan.log_file,
                raw_destination=plan.raw_file,
            )
        except Exception:
            restore_output_backups(output_backups)
            raise
        discard_output_backups(output_backups)
        return _build_run(
            adapter_key=adapter.key,
            plan=plan,
            dry_run=False,
            exit_code=cached_entry.exit_code,
            duration_s=cached_entry.duration_s,
            stdout=cached_entry.stdout,
            stderr=cached_entry.stderr,
            cached=True,
            cache_key=cache_key,
        )

    plan.log_file.parent.mkdir(parents=True, exist_ok=True)
    plan.raw_file.parent.mkdir(parents=True, exist_ok=True)
    output_backups = prepare_output_backups((plan.log_file, plan.raw_file), label="run-backup")

    try:
        try:
            process = run_subprocess_with_log_progress(
                plan.command,
                cwd=plan.working_directory,
                log_path=plan.log_file,
                timeout_s=effective_timeout_s,
                run_id=run_id,
            )
        except subprocess.TimeoutExpired as exc:
            stderr = (
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            )
            raise SimulationTimeoutError(
                f"QSpice timed out after {effective_timeout_s} seconds.",
                stderr=stderr,
            ) from exc

        if run_id is not None and consume_run_cancellation(run_id):
            raise SimulationError(  # noqa: TRY301
                f"Simulation run {run_id!r} was cancelled by request.",
                exit_code=process.exit_code,
                stderr=process.stderr,
            )

        _classify_log_failure(
            adapter=adapter,
            plan=plan,
            process_exit_code=process.exit_code,
            stderr=process.stderr,
            probe_version=probe.version,
        )

        if process.exit_code != 0:
            _raise_nonzero_exit_error(exit_code=process.exit_code, stderr=process.stderr)
    except Exception:
        restore_output_backups(output_backups)
        raise

    discard_output_backups(output_backups)

    if plan.log_file.is_file() and plan.raw_file.is_file():
        cache.put(
            cache_key,
            log_source=plan.log_file,
            raw_source=plan.raw_file,
            exit_code=process.exit_code,
            duration_s=process.duration_s,
            stdout=process.stdout,
            stderr=process.stderr,
        )

    return _build_run(
        adapter_key=adapter.key,
        plan=plan,
        dry_run=False,
        exit_code=process.exit_code,
        duration_s=process.duration_s,
        stdout=process.stdout,
        stderr=process.stderr,
        cache_key=cache_key,
    )


__all__ = ["SERVICE_SPEC", "SimulationRun", "run_simulation"]
