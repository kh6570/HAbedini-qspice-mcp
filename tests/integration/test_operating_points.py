"""Integration coverage for Phase 6 operating-point services."""

from __future__ import annotations

from pathlib import Path
from shutil import copy2

import pytest

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.filter_device_operating_points import (
    filter_device_operating_points,
)
from qspice_mcp.services.waveform.read_device_operating_points import (
    read_device_operating_points,
)
from qspice_mcp.services.waveform.summarize_device_operating_points import (
    summarize_device_operating_points,
)

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


def test_operating_point_fixture_can_be_read_and_summarized(tmp_path: Path) -> None:
    """A real `.op` fixture should produce readable operating-point data."""

    executable = _require_local_qspice_runtime(tmp_path)
    source_netlist = FIXTURE_ROOT / "netlists" / "op_probe.net"
    netlist = tmp_path / source_netlist.name
    copy2(source_netlist, netlist)

    result = run_simulation(
        netlist,
        workspace_root=tmp_path,
        settings=QSpiceSettings(exe=executable, workspace_root=tmp_path),
        log_path=tmp_path / "op_probe.log",
        raw_output_path=tmp_path / "op_probe.qraw",
    )

    catalog = read_device_operating_points(result.raw_path, workspace_root=tmp_path)
    summary = summarize_device_operating_points(result.raw_path, workspace_root=tmp_path)
    filtered = filter_device_operating_points(
        result.raw_path,
        workspace_root=tmp_path,
        families=("mosfet",),
        metric_names=("power", "drain_current"),
    )

    assert result.exit_code == 0
    assert result.raw_exists is True
    assert catalog.plot_name == "Operating Point"
    assert catalog.device_count >= 4
    assert any(device.reference == "M1" for device in catalog.devices)
    assert summary.highest_dissipation is not None
    assert summary.highest_node_voltage is not None
    assert filtered.device_count == 1
    assert filtered.devices[0].reference == "M1"
