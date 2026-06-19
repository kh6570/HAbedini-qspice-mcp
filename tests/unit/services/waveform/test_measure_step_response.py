"""Tests for step-response measurement."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import numpy as np
import pytest

from qspice_mcp.services.waveform.measure_step_response import measure_step_response

if TYPE_CHECKING:
    from pathlib import Path

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")


class FakeStepRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0], dtype=np.float64)
        self._wave = np.array([0.0, 0.0, 0.5, 1.15, 1.05, 1.01, 1.0, 1.0], dtype=np.float64)

    def get_trace_names(self) -> list[str]:
        return ["time", "V(out)"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(1)

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
        return self._wave

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_measure_step_response_computes_metrics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "step.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeStepRawRead, "fake-backend")
    )

    result = measure_step_response(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        initial_value=0.0,
        final_value=1.0,
    )

    assert result.rise_time_s == pytest.approx(1.42, rel=0.05)
    assert result.delay_time_s == pytest.approx(2.0, rel=0.1)
    assert result.overshoot_pct == pytest.approx(15.0, rel=0.1)
    assert result.settling_time_s == pytest.approx(5.0, rel=0.1)
    assert result.peak_value == pytest.approx(1.15)
