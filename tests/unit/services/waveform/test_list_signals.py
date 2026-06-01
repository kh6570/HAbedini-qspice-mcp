"""Tests for the RawRead-backed list_signals service."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services.waveform.list_signals import list_signals

if TYPE_CHECKING:
    import pytest

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
BODE_RAW_FIXTURE = FIXTURE_ROOT / "bode-only.qraw"
BODE_LOG_FIXTURE = FIXTURE_ROOT / "bode-only.log"


class FakeRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float64)
        self._waves = {
            "V(out)": np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64),
            "I(L1)": np.array([0.0, -0.5, 0.5, -0.5, 0.5], dtype=np.float64),
            "V(ac)": np.array([1 + 1j, 2 + 2j, 3 + 3j, 4 + 4j, 5 + 5j], dtype=np.complex128),
        }

    def get_trace_names(self) -> list[str]:
        return ["time", *self._waves.keys()]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(2)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> np.ndarray:
        del step
        return self._axis

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        del step
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "time":
            return self._axis
        return self._waves[trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_list_signals_summarizes_available_traces(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = list_signals(raw_path, workspace_root=tmp_path)

    assert result.raw_path == raw_path.resolve(strict=False)
    assert result.plot_name == "Transient Analysis"
    assert result.axis_name == "time"
    assert result.axis_unit == "s"
    assert result.step_count == 2
    assert result.point_count == 5
    assert result.signal_count == 3
    assert result.resolved_step == 0
    assert tuple(signal.name for signal in result.signals) == ("V(out)", "I(L1)", "V(ac)")
    assert result.signals[1].unit == "A"
    assert result.signals[2].complex_data is True


class FakeSteppedRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axes = {
            0: np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float64),
            1: np.array([0.0, 1.0, 2.0], dtype=np.float64),
        }
        self._waves = {
            0: {"V(out)": np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64)},
            1: {"V(out)": np.array([5.0, 6.0, 7.0], dtype=np.float64)},
        }

    def get_trace_names(self) -> list[str]:
        return ["time", "V(out)"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(2)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> np.ndarray:
        return self._axes[step]

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "time":
            return self._axes[step]
        return self._waves[step][trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_list_signals_resolves_step_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeSteppedRawRead, "fake-backend")
    )
    monkeypatch.setattr(
        waveform_backend,
        "_read_step_variables_for_raw",
        lambda raw_path, *, workspace_root: (
            waveform_backend.LogStepVariable(name="vin", values=(10, 12)),
        ),
    )

    result = list_signals(raw_path, workspace_root=tmp_path, step_filters={"VIN": 12})

    assert result.resolved_step == 1
    assert result.point_count == 3
    assert result.signals[0].point_count == 3


def test_list_signals_reads_external_ac_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    log_path = tmp_path / BODE_LOG_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)
    copy2(BODE_LOG_FIXTURE, log_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = list_signals(raw_path, workspace_root=tmp_path)

    assert result.plot_name == "AC Analysis"
    assert result.axis_name == "Frequency"
    assert result.step_count == 1
    assert result.point_count == 5220
    assert result.signal_count == 1
    assert result.signals[0].name == "OpenLoopGain"
    assert result.signals[0].complex_data is True
