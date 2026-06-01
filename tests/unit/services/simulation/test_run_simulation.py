"""Tests for the run_simulation service."""

from __future__ import annotations

import importlib
import subprocess
from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import (
    ConvergenceError,
    SimulationError,
    SimulationTimeoutError,
    ValidationError,
)
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.subprocess import SubprocessResult
from qspice_mcp.services.simulation.run_simulation import run_simulation

if TYPE_CHECKING:
    from pathlib import Path

run_simulation_service = importlib.import_module("qspice_mcp.services.simulation.run_simulation")


def test_run_simulation_dry_run_returns_command_plan(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    result = run_simulation(
        "demo.net",
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        dry_run=True,
        ascii_raw=True,
        extra_switches=("-BSIM1",),
    )

    resolved_netlist = netlist.resolve()
    assert result.dry_run is True
    assert result.command == (
        str(executable.resolve()),
        "-o",
        str(resolved_netlist.with_suffix(".log")),
        str(resolved_netlist),
        "-r",
        str(resolved_netlist.with_suffix(".qraw")),
        "-ASCII",
        "-BSIM1",
    )
    assert result.netlist_path == resolved_netlist
    assert result.log_path == resolved_netlist.with_suffix(".log")
    assert result.raw_path == resolved_netlist.with_suffix(".qraw")
    assert result.exit_code is None


def test_run_simulation_executes_via_subprocess_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.cir"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = tmp_path / "artifacts" / "demo.log"
    raw_path = tmp_path / "artifacts" / "demo.qraw"

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("ok", encoding="utf-8")
        raw_path.write_text("raw", encoding="utf-8")
        assert cwd == netlist.resolve().parent
        assert timeout_s == 12.5
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.25,
            stdout="stdout",
            stderr="",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fake_run_subprocess)

    result = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        timeout_s=12.5,
        log_path=log_path,
        raw_output_path=raw_path,
    )

    assert result.dry_run is False
    assert result.exit_code == 0
    assert result.duration_s == 0.25
    assert result.stdout == "stdout"
    assert result.log_exists is True
    assert result.raw_exists is True


def test_run_simulation_reuses_cached_artifacts_without_rerunning_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    first_log = tmp_path / "artifacts" / "first.log"
    first_raw = tmp_path / "artifacts" / "first.qraw"
    second_log = tmp_path / "artifacts" / "second.log"
    second_raw = tmp_path / "artifacts" / "second.qraw"
    settings = QSpiceSettings(
        exe=executable,
        workspace_root=tmp_path,
        cache_dir=tmp_path / ".cache",
    )

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        del command, cwd, timeout_s
        first_log.parent.mkdir(parents=True, exist_ok=True)
        first_log.write_text("log from subprocess\n", encoding="utf-8")
        first_raw.write_text("raw from subprocess\n", encoding="utf-8")
        return SubprocessResult(
            command=("QSPICE64.exe", str(netlist.resolve(strict=False))),
            working_directory=tmp_path,
            exit_code=0,
            duration_s=0.25,
            stdout="stdout",
            stderr="",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fake_run_subprocess)

    first = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=settings,
        log_path=first_log,
        raw_output_path=first_raw,
    )

    monkeypatch.setattr(
        run_simulation_service,
        "run_subprocess",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("cache miss")),
    )

    second = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=settings,
        log_path=second_log,
        raw_output_path=second_raw,
    )

    assert first.cached is False
    assert first.cache_key is not None
    assert second.cached is True
    assert second.cache_key == first.cache_key
    assert second.stdout == "stdout"
    assert second_log.read_text(encoding="utf-8") == "log from subprocess\n"
    assert second_raw.read_text(encoding="utf-8") == "raw from subprocess\n"


def test_run_simulation_invalidates_stale_cache_entry_and_reruns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = tmp_path / "artifacts" / "demo.log"
    raw_path = tmp_path / "artifacts" / "demo.qraw"
    settings = QSpiceSettings(
        exe=executable,
        workspace_root=tmp_path,
        cache_dir=tmp_path / ".cache",
    )
    call_count = 0

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        nonlocal call_count
        del command, cwd, timeout_s
        call_count += 1
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"log {call_count}\n", encoding="utf-8")
        raw_path.write_text(f"raw {call_count}\n", encoding="utf-8")
        return SubprocessResult(
            command=("QSPICE64.exe", str(netlist.resolve(strict=False))),
            working_directory=tmp_path,
            exit_code=0,
            duration_s=0.1,
            stdout=f"stdout {call_count}",
            stderr="",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fake_run_subprocess)

    first = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=settings,
        log_path=log_path,
        raw_output_path=raw_path,
    )
    assert first.cache_key is not None

    cached_raw = settings.normalized().cache_dir / "simulation" / first.cache_key / "artifacts.qraw"
    cached_raw.unlink()

    second = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=settings,
        log_path=log_path,
        raw_output_path=raw_path,
    )

    assert call_count == 2
    assert second.cached is False
    assert second.stdout == "stdout 2"


def test_run_simulation_rejects_positional_or_pathlike_extra_switches(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="dash-prefixed flags"):
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
            dry_run=True,
            extra_switches=("other.log",),
        )

    with pytest.raises(ValidationError, match="path-like values"):
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
            dry_run=True,
            extra_switches=(r"-Config=C:\temp\outside.cfg",),
        )


def test_run_simulation_maps_nonzero_exit_to_domain_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    monkeypatch.setattr(
        run_simulation_service,
        "run_subprocess",
        lambda command, *, cwd, timeout_s: SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=7,
            duration_s=0.1,
            stdout="",
            stderr="fatal",
        ),
    )

    with pytest.raises(SimulationError) as exc_info:
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        )

    assert exc_info.value.exit_code == 7
    assert exc_info.value.stderr == "fatal"


def test_run_simulation_raises_convergence_error_from_log_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = netlist.with_suffix(".log")

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        log_path.write_text("Transient analysis failed: time step too small\n", encoding="utf-8")
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.2,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fake_run_subprocess)

    with pytest.raises(ConvergenceError) as exc_info:
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        )

    assert exc_info.value.exit_code == 0
    assert exc_info.value.stderr is not None
    assert "time step too small" in exc_info.value.stderr.lower()


def test_run_simulation_raises_simulation_error_from_fatal_log_signature(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = netlist.with_suffix(".log")

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        log_path.write_text("Fatal error: missing model definition\n", encoding="utf-8")
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.2,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fake_run_subprocess)

    with pytest.raises(SimulationError) as exc_info:
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        )

    assert type(exc_info.value) is SimulationError
    assert exc_info.value.exit_code == 0
    assert exc_info.value.stderr is not None
    assert "fatal error" in exc_info.value.stderr.lower()


def test_run_simulation_maps_timeout_to_domain_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = netlist.with_suffix(".log")
    raw_path = netlist.with_suffix(".qraw")
    log_path.write_text("previous log\n", encoding="utf-8")
    raw_path.write_text("previous raw\n", encoding="utf-8")

    def raise_timeout(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        del cwd
        log_path.write_text("partial log\n", encoding="utf-8")
        raw_path.write_text("partial raw\n", encoding="utf-8")
        raise subprocess.TimeoutExpired(command, timeout_s or 0.0, stderr="timed out")

    monkeypatch.setattr(run_simulation_service, "run_subprocess", raise_timeout)

    with pytest.raises(SimulationTimeoutError) as exc_info:
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
            timeout_s=1.5,
        )

    assert exc_info.value.stderr == "timed out"
    assert log_path.read_text(encoding="utf-8") == "previous log\n"
    assert raw_path.read_text(encoding="utf-8") == "previous raw\n"


def test_run_simulation_restores_previous_outputs_after_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_path = netlist.with_suffix(".log")
    raw_path = netlist.with_suffix(".qraw")
    log_path.write_text("previous log\n", encoding="utf-8")
    raw_path.write_text("previous raw\n", encoding="utf-8")

    def fail_with_partial_outputs(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None
    ) -> SubprocessResult:
        del command, cwd, timeout_s
        log_path.write_text("new partial log\n", encoding="utf-8")
        raw_path.write_text("new partial raw\n", encoding="utf-8")
        return SubprocessResult(
            command=("QSPICE64.exe",),
            working_directory=tmp_path,
            exit_code=9,
            duration_s=0.1,
            stdout="",
            stderr="fatal",
        )

    monkeypatch.setattr(run_simulation_service, "run_subprocess", fail_with_partial_outputs)

    with pytest.raises(SimulationError) as exc_info:
        run_simulation(
            netlist,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        )

    assert exc_info.value.exit_code == 9
    assert log_path.read_text(encoding="utf-8") == "previous log\n"
    assert raw_path.read_text(encoding="utf-8") == "previous raw\n"
