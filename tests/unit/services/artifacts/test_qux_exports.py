"""Tests for QUX-backed waveform and DLL export services."""

from __future__ import annotations

import importlib
import subprocess
from types import SimpleNamespace

import pytest

from qspice_mcp.core.exceptions import SimulationTimeoutError, ValidationError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.subprocess import SubprocessResult
from qspice_mcp.services.artifacts.export_touchstone_s2p import export_touchstone_s2p
from qspice_mcp.services.artifacts.export_waveform_ascii import export_waveform_ascii
from qspice_mcp.services.artifacts.export_waveform_csv import export_waveform_csv
from qspice_mcp.services.artifacts.generate_dll_variables import generate_dll_variables

qux_exports = importlib.import_module("qspice_mcp.services.artifacts._qux_export")
qux_internal = importlib.import_module("qspice_mcp.services._internals.qux")


def test_export_waveform_ascii_writes_exported_text(monkeypatch, tmp_path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")
    qux_executable = tmp_path / "QUX.exe"
    qux_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=qux_executable.resolve(strict=False),
        ),
    )
    monkeypatch.setattr(
        qux_exports,
        "run_qux_command",
        lambda command, *, cwd, timeout_s=None: SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="0,1\n1,2\n",
            stderr="",
        ),
    )

    exported = export_waveform_ascii(
        raw_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
        expressions=["V(out)"],
    )

    assert exported.format == "ASCII"
    assert exported.output_path.read_text(encoding="utf-8") == "0,1\n1,2\n"
    assert exported.command[1] == "-Export"


def test_export_waveform_csv_uses_csv_suffix(monkeypatch, tmp_path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")
    qux_executable = tmp_path / "QUX.exe"
    qux_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=qux_executable.resolve(strict=False),
        ),
    )
    monkeypatch.setattr(
        qux_exports,
        "run_qux_command",
        lambda command, *, cwd, timeout_s=None: SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="time,V(out)\n0,1\n",
            stderr="",
        ),
    )

    exported = export_waveform_csv(
        raw_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
        expressions=["V(out)"],
    )

    assert exported.format == "CSV"
    assert exported.output_path.suffix.lower() == ".csv"
    assert exported.output_path.read_text(encoding="utf-8") == "time,V(out)\n0,1\n"


def test_export_touchstone_s2p_uses_s2p_format(monkeypatch, tmp_path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")
    qux_executable = tmp_path / "QUX.exe"
    qux_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=qux_executable.resolve(strict=False),
        ),
    )
    monkeypatch.setattr(
        qux_exports,
        "run_qux_command",
        lambda command, *, cwd, timeout_s=None: SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="# Hz S RI R 50\n1 0 0 0 0\n",
            stderr="",
        ),
    )

    exported = export_touchstone_s2p(
        raw_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
        expressions=["V(out)", "I(V1)"],
    )

    assert exported.format == "S2P"
    assert exported.output_path.suffix.lower() == ".s2p"


def test_generate_dll_variables_writes_text_artifact(monkeypatch, tmp_path) -> None:
    schematic_path = tmp_path / "demo.qsch"
    schematic_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")
    qux_executable = tmp_path / "QUX.exe"
    qux_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=qux_executable.resolve(strict=False),
        ),
    )
    monkeypatch.setattr(
        qux_exports,
        "run_qux_command",
        lambda command, *, cwd, timeout_s=None: SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="double VIN;\ndouble VOUT;\n",
            stderr="",
        ),
    )

    exported = generate_dll_variables(
        schematic_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
    )

    assert exported.line_count == 2
    assert exported.output_path.read_text(encoding="utf-8") == "double VIN;\ndouble VOUT;\n"
    assert exported.command[1] == "-DLLvariables"


def test_export_waveform_csv_rejects_non_csv_output_paths(monkeypatch, tmp_path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
        ),
    )

    with pytest.raises(ValidationError, match=r"\.csv"):
        export_waveform_csv(
            raw_path,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
            expressions=["V(out)"],
            output_path=tmp_path / "trace.txt",
        )


def test_generate_dll_variables_rejects_non_text_output_paths(monkeypatch, tmp_path) -> None:
    schematic_path = tmp_path / "demo.qsch"
    schematic_path.write_text("", encoding="utf-8")
    qspice_executable = tmp_path / "QSPICE64.exe"
    qspice_executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        qux_exports,
        "resolve_qux_companion",
        lambda settings: SimpleNamespace(
            qspice_executable=qspice_executable.resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
        ),
    )

    with pytest.raises(ValidationError, match=r"\.dllvars\.txt"):
        generate_dll_variables(
            schematic_path,
            workspace_root=tmp_path,
            settings=QSpiceSettings(exe=qspice_executable, workspace_root=tmp_path),
            output_path=tmp_path / "vars.txt",
        )


def test_build_qux_export_command_rejects_switch_like_expressions(tmp_path) -> None:
    qux_path = tmp_path / "QUX.exe"
    raw_path = tmp_path / "demo.qraw"

    with pytest.raises(ValidationError, match="cannot start with '-'"):
        qux_exports.build_qux_export_command(
            qux_path,
            raw_path,
            expressions=("-stdout",),
            export_format="csv",
        )


def test_run_qux_command_maps_timeout_to_domain_error(monkeypatch, tmp_path) -> None:
    command = ("QUX.exe", "-Export", "demo.qraw", "V(out)", "CSV")

    def raise_timeout(command, *, cwd, timeout_s):
        raise subprocess.TimeoutExpired(command, timeout_s or 0.0, stderr="timed out")

    monkeypatch.setattr(qux_internal, "run_subprocess", raise_timeout)

    with pytest.raises(SimulationTimeoutError, match="timed out"):
        qux_internal.run_qux_command(command, cwd=tmp_path, timeout_s=1.0)
