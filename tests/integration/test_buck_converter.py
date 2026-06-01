"""Integration coverage for the Buck Converter example schematic."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.list_signals import list_signals
from qspice_mcp.services.waveform.measure_waveform import measure_waveform
from qspice_mcp.services.waveform.plot_waveforms import plot_waveforms
from qspice_mcp.services.waveform.read_waveform import read_waveform

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_local_qspice_runtime(workspace_root: Path) -> Path:
    """Skip when the local machine cannot run QSpice-backed integration tests."""

    pytest.skip("optional backend unavailable")
    probe = probe_qspice(QSpiceSettings(workspace_root=workspace_root))
    if probe.executable is None or not probe.exists:
        pytest.skip("QSpice executable is not available for integration tests.")
    return probe.executable


def test_buck_converter_example_can_generate_and_run(tmp_path: Path) -> None:
    """The portable example schematic should convert to a netlist and simulate."""

    executable = _require_local_qspice_runtime(tmp_path)
    schematic = tmp_path / "Buck-converter.qsch"
    schematic.write_bytes(
        (files("qspice_mcp.data.recipes") / "buck_converter_cpp" / "Buck-converter.qsch").read_bytes()
    )

    generated = generate_netlist(
        schematic,
        workspace_root=tmp_path,
        output_path=tmp_path / "Buck-converter.net",
    )

    assert generated.source_kind == "schematic"
    assert generated.refreshed is True
    assert generated.copied is False
    assert generated.netlist_path.is_file()

    result = run_simulation(
        generated.netlist_path,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        log_path=tmp_path / "buck.log",
        raw_output_path=tmp_path / "buck.qraw",
    )

    assert result.exit_code == 0
    assert result.log_exists is True
    assert result.raw_exists is True

    signal_catalog = list_signals(result.raw_path, workspace_root=tmp_path)
    assert any(signal.name == "V(out)" for signal in signal_catalog.signals)

    waveform = read_waveform(
        result.raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        max_points=256,
    )
    assert waveform.point_count <= 256
    assert waveform.y_values[-1] > 4.0

    rms = measure_waveform(
        result.raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        operation="rms",
    )
    assert rms.value > 1.0

    plot = plot_waveforms(
        result.raw_path,
        workspace_root=tmp_path,
        signals=("V(out)",),
        output_path=tmp_path / "plots" / "buck-vout.png",
        max_points=512,
        title="Buck Converter Output",
    )
    assert plot.plot_path.is_file()
    assert plot.plot_path.stat().st_size > 0
