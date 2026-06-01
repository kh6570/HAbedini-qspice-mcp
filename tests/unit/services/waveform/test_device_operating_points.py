"""Tests for Phase 6 operating-point services."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services.waveform.filter_device_operating_points import (
    filter_device_operating_points,
)
from qspice_mcp.services.waveform.read_device_operating_points import (
    read_device_operating_points,
)
from qspice_mcp.services.waveform.summarize_device_operating_points import (
    summarize_device_operating_points,
)

if TYPE_CHECKING:
    import pytest

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
NETLIST_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "netlists" / "op_probe.net"
RAW_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "qraw" / "op_probe.qraw"
LOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "qraw" / "op_probe.log"


class FakeOperatingPointRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._waves = {
            "V(in)": np.array([10.0], dtype=np.float64),
            "V(out)": np.array([0.7], dtype=np.float64),
            "I(V1)": np.array([-0.02], dtype=np.float64),
            "I(R1)": np.array([0.01], dtype=np.float64),
            "I(D1)": np.array([0.004], dtype=np.float64),
            "Id(M1)": np.array([0.006], dtype=np.float64),
            "Is(M1)": np.array([-0.006], dtype=np.float64),
            "Ig(M1)": np.array([0.0], dtype=np.float64),
            "Ib(M1)": np.array([0.0], dtype=np.float64),
            "P(V1)": np.array([-0.2], dtype=np.float64),
            "P(R1)": np.array([0.1], dtype=np.float64),
            "P(D1)": np.array([0.003], dtype=np.float64),
            "P(M1)": np.array([0.004], dtype=np.float64),
        }

    def get_trace_names(self) -> list[str]:
        return list(self._waves)

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(1)

    def has_axis(self) -> bool:
        return False

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        del step
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        return self._waves[trace_ref]

    def get_plot_name(self) -> str:
        return "Operating Point"


def _write_demo_netlist(netlist_path: Path) -> None:
    netlist_path.write_text(
        "\n".join(
            (
                "* operating point demo",
                "V1 in 0 10",
                "R1 in out 1k",
                "D1 out 0 DTEST",
                "M1 out in 0 0 NMOS",
                ".model DTEST D(IS=1e-14)",
                ".model NMOS NMOS (VTO=2 KP=1m)",
                ".option KEEPOPINFO",
                ".option SAVEPOWERS",
                ".op",
                ".end",
            )
        )
        + "\n",
        encoding="utf-8",
    )


def test_read_device_operating_points_groups_metrics_by_device(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "op_probe.qraw"
    raw_path.write_text("", encoding="utf-8")
    netlist_path = tmp_path / "op_probe.net"
    _write_demo_netlist(netlist_path)
    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeOperatingPointRawRead, "fake-backend"),
    )

    result = read_device_operating_points(raw_path, workspace_root=tmp_path)

    by_reference = {device.reference: device for device in result.devices}

    assert result.plot_name == "Operating Point"
    assert result.netlist_path == netlist_path.resolve(strict=False)
    assert result.device_count == 4
    assert result.node_count == 2
    assert result.node_voltages[0].node == "in"
    assert by_reference["M1"].family == "mosfet"
    assert by_reference["M1"].model == "NMOS"
    assert by_reference["M1"].model_type == "nmos"
    assert by_reference["M1"].nodes == ("out", "in", "0", "0")
    assert {metric.name for metric in by_reference["M1"].metrics} == {
        "bulk_current",
        "drain_current",
        "gate_current",
        "power",
        "source_current",
    }
    assert by_reference["D1"].model == "DTEST"
    assert by_reference["R1"].family == "resistor"


def test_summarize_device_operating_points_reports_extrema(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "op_probe.qraw"
    raw_path.write_text("", encoding="utf-8")
    netlist_path = tmp_path / "op_probe.net"
    _write_demo_netlist(netlist_path)
    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeOperatingPointRawRead, "fake-backend"),
    )

    result = summarize_device_operating_points(raw_path, workspace_root=tmp_path)

    family_counts = {summary.family: summary.device_count for summary in result.family_summaries}

    assert family_counts == {
        "diode": 1,
        "mosfet": 1,
        "resistor": 1,
        "voltage_source": 1,
    }
    assert result.highest_dissipation is not None
    assert result.highest_dissipation.reference == "R1"
    assert result.lowest_dissipation is not None
    assert result.lowest_dissipation.reference == "V1"
    assert result.largest_abs_current is not None
    assert result.largest_abs_current.reference == "V1"
    assert result.highest_node_voltage is not None
    assert result.highest_node_voltage.node == "in"
    assert result.lowest_node_voltage is not None
    assert result.lowest_node_voltage.node == "out"


def test_filter_device_operating_points_selects_by_family_and_metric_presence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "op_probe.qraw"
    raw_path.write_text("", encoding="utf-8")
    netlist_path = tmp_path / "op_probe.net"
    _write_demo_netlist(netlist_path)
    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeOperatingPointRawRead, "fake-backend"),
    )

    result = filter_device_operating_points(
        raw_path,
        workspace_root=tmp_path,
        families=("mosfet",),
        metric_names=("power", "drain_current"),
    )

    assert result.original_device_count == 4
    assert result.device_count == 1
    assert result.devices[0].reference == "M1"
    assert result.applied_filters.families == ("mosfet",)
    assert result.applied_filters.metric_names == ("drain_current", "power")


def test_read_device_operating_points_reads_recorded_savepowers_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / RAW_FIXTURE.name
    log_path = tmp_path / LOG_FIXTURE.name
    netlist_path = tmp_path / NETLIST_FIXTURE.name
    copy2(RAW_FIXTURE, raw_path)
    copy2(LOG_FIXTURE, log_path)
    copy2(NETLIST_FIXTURE, netlist_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_device_operating_points(raw_path, workspace_root=tmp_path)

    by_reference = {device.reference: device for device in result.devices}
    assert result.plot_name == "Operating Point"
    assert result.netlist_path == netlist_path.resolve(strict=False)
    assert result.device_count == 4
    assert result.node_count == 1
    assert result.warnings == ()
    assert result.node_voltages[0].node == "out"
    assert set(by_reference) == {"D1", "M1", "R1", "V1"}
    assert by_reference["R1"].family == "resistor"
    assert {metric.name for metric in by_reference["V1"].metrics} == {"current", "power"}
