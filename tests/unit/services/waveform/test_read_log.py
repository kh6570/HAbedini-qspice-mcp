"""Tests for the QPOST-backed read_log service."""

from __future__ import annotations

import importlib
import subprocess
from pathlib import Path

import pytest

from qspice_mcp.core.exceptions import SimulationTimeoutError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.subprocess import SubprocessResult
from qspice_mcp.services.waveform.read_log import read_log

read_log_service = importlib.import_module("qspice_mcp.services.waveform.read_log")


def test_read_log_extracts_steps_and_measures_via_qpost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    qpost = tmp_path / "QPOST.exe"
    qpost.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text(
        " 1 of 2 steps: .step cap=1e-6 mode=1\n"
        " 2 of 2 steps: .step cap=2e-6 mode=2\n"
        "warning line\n",
        encoding="utf-8",
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None = None
    ) -> SubprocessResult:
        assert command[:3] == (str(qpost.resolve()), str(netlist.resolve()), "-o")
        assert Path(command[3]).suffix == ".meas"
        assert Path(command[3]) != log_path.with_suffix(".meas").resolve(strict=False)
        assert cwd == tmp_path.resolve()
        Path(command[3]).write_text(
            ".meas tran vmax MAX V(out)\n"
            "1 3.2\n"
            "2 3.4\n"
            ".meas tran delay TRIG V(out)\n"
            "1 0.1 0.2\n"
            "2 0.3 0.4\n",
            encoding="utf-8",
        )
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.05,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(read_log_service, "run_subprocess", fake_run_subprocess)

    result = read_log(
        log_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        max_lines=2,
    )

    assert result.step_count == 2
    assert result.step_variables[0].name == "cap"
    assert result.step_variables[0].values == (1e-06, 2e-06)
    assert result.step_variables[1].name == "mode"
    assert result.step_variables[1].values == (1, 2)
    assert result.meas_path == log_path.with_suffix(".meas").resolve(strict=False)
    assert result.qpost_command is not None
    assert result.measures[0].name == "vmax"
    assert result.measures[0].columns == ("step", "vmax")
    assert result.measures[0].rows == ((1, 3.2), (2, 3.4))
    assert result.measures[1].columns == ("step", "delay", "delay_1")
    assert result.excerpt == " 2 of 2 steps: .step cap=2e-6 mode=2\nwarning line"


def test_read_log_maps_qpost_timeout_and_cleans_staged_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    qpost = tmp_path / "QPOST.exe"
    qpost.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text("plain log\n", encoding="utf-8")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    meas_path = log_path.with_suffix(".meas")
    meas_path.write_text("stale\n", encoding="utf-8")
    staged_paths: list[Path] = []

    def fake_run_subprocess(
        command: tuple[str, ...], *, cwd: Path, timeout_s: float | None = None
    ) -> SubprocessResult:
        del cwd
        staged_path = Path(command[3])
        staged_paths.append(staged_path)
        staged_path.write_text("partial\n", encoding="utf-8")
        raise subprocess.TimeoutExpired(command, timeout_s or 0.0, stderr="timed out")

    monkeypatch.setattr(read_log_service, "run_subprocess", fake_run_subprocess)

    with pytest.raises(SimulationTimeoutError, match=r"QPOST timed out after 1\.5 seconds"):
        read_log(
            log_path,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
            timeout_s=1.5,
        )

    assert staged_paths
    assert staged_paths[0].exists() is False
    assert meas_path.read_text(encoding="utf-8") == "stale\n"


def test_read_log_bounds_measure_rows_when_requested(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text("plain log\n", encoding="utf-8")
    log_path.with_suffix(".meas").write_text(
        ".meas tran vmax MAX V(out)\n1.0\n2.0\n3.0\n",
        encoding="utf-8",
    )

    result = read_log(
        log_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        refresh_measures=False,
        max_measure_rows=2,
    )

    assert result.measures[0].rows == ((1.0,), (2.0,))
    assert result.measure_rows_truncated is True


def test_read_log_reports_missing_netlist_when_qpost_cannot_run(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    qpost = tmp_path / "QPOST.exe"
    qpost.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text("plain log\n", encoding="utf-8")

    result = read_log(
        log_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
    )

    assert result.measures == ()
    assert result.qpost_command is None
    assert "No sibling .net or .cir file" in result.warnings[0]
