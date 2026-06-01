"""Integration coverage for real Phase 9 and Phase 10 fixtures."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2

import pytest

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.artifacts.describe_qux_export_support import (
    describe_qux_export_support,
)
from qspice_mcp.services.artifacts.export_waveform_ascii import export_waveform_ascii
from qspice_mcp.services.simulation.prepare_bode_analysis import prepare_bode_analysis
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.list_signals import list_signals
from qspice_mcp.services.waveform.measure_bode_response import measure_bode_response

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures"


def _require_local_qspice_runtime(workspace_root: Path) -> Path:
    """Skip when the local machine cannot run QSpice-backed integration tests."""

    pytest.skip("optional backend unavailable")
    probe = probe_qspice(QSpiceSettings(workspace_root=workspace_root))
    if probe.executable is None or not probe.exists:
        pytest.skip("QSpice executable is not available for integration tests.")
    return probe.executable


def _require_local_qux_support(workspace_root: Path) -> Path:
    """Skip when the companion QUX runtime is unavailable locally."""

    support = describe_qux_export_support(settings=QSpiceSettings(workspace_root=workspace_root))
    if not support.available or support.qspice_executable is None:
        pytest.skip("QUX companion is not available for integration tests.")
    return support.qspice_executable


def test_bode_fixture_can_stage_and_measure_response(tmp_path: Path) -> None:
    """A real `.bode` fixture should produce measurable frequency-domain output."""

    executable = _require_local_qspice_runtime(tmp_path)
    source_netlist = FIXTURE_ROOT / "netlists" / "closed_loop_regulator.net"
    netlist = tmp_path / source_netlist.name
    copy2(source_netlist, netlist)

    prepared = prepare_bode_analysis(
        netlist,
        workspace_root=tmp_path,
        perturbation_source="VPERT",
        settling_time="2m",
        start_frequency="100",
        stop_frequency="100k",
        injection_amplitude="5m",
        output_path=tmp_path / "closed_loop_regulator-bode.net",
    )

    assert prepared.source_kind == "netlist"
    assert prepared.output_path.is_file()
    assert prepared.instruction == ".bode VPERT 2m 100 100k 5m"

    result = run_simulation(
        prepared.output_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        log_path=tmp_path / "closed_loop_regulator-bode.log",
        raw_output_path=tmp_path / "closed_loop_regulator-bode.qraw",
    )

    assert result.exit_code == 0
    assert result.log_exists is True
    assert result.raw_exists is True

    catalog = list_signals(result.raw_path, workspace_root=tmp_path)
    measurement = measure_bode_response(
        result.raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        frequencies_hz=(100.0, 1_000.0, 10_000.0),
    )

    assert result.raw_path.stat().st_size > 0
    assert catalog.plot_name == "AC Analysis"
    assert catalog.axis_name == "Frequency"
    assert any(signal.name == "OpenLoopGain" for signal in catalog.signals)
    assert measurement.plot_name == "AC Analysis"
    assert measurement.axis_name == "Frequency"
    assert measurement.signal == "OpenLoopGain"
    assert measurement.sample_count >= 3
    assert tuple(sample.frequency_hz for sample in measurement.samples) == (
        100.0,
        1_000.0,
        10_000.0,
    )


def test_qux_export_fixture_can_emit_ascii(tmp_path: Path) -> None:
    """A real `.qraw` fixture should export through the local QUX companion."""

    executable = _require_local_qux_support(tmp_path)
    source_raw = FIXTURE_ROOT / "qraw" / "qux_export_source.qraw"
    raw_path = tmp_path / source_raw.name
    copy2(source_raw, raw_path)

    exported = export_waveform_ascii(
        raw_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        expressions=("V(out)",),
        point_count=128,
        output_path=tmp_path / "exports" / "qux-export.ascii.txt",
    )

    assert exported.output_path.is_file()
    assert exported.output_path.stat().st_size > 0
    assert exported.format == "ASCII"
    assert exported.expressions == ("V(out)",)
    assert exported.line_count >= 2
    assert "-Export" in exported.command
