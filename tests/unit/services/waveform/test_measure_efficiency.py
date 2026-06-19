"""Tests for transient power efficiency measurement."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import numpy as np
import pytest

from qspice_mcp.services.waveform.measure_efficiency import measure_efficiency

if TYPE_CHECKING:
    from pathlib import Path

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")


class FakePowerRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([0.0, 1.0, 2.0], dtype=np.float64)
        self._waves = {
            "p(V1)": np.array([10.0, 10.0, 10.0], dtype=np.float64),
            "p(R1)": np.array([8.0, 8.0, 8.0], dtype=np.float64),
        }

    def get_trace_names(self) -> list[str]:
        return ["time", "p(V1)", "p(R1)"]

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
        return self._waves[trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_measure_efficiency_computes_average_powers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "power.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakePowerRawRead, "fake-backend")
    )

    result = measure_efficiency(
        raw_path,
        workspace_root=tmp_path,
        input_power_signal="p(V1)",
        output_power_signal="p(R1)",
    )

    assert result.average_input_power_w == pytest.approx(10.0)
    assert result.average_output_power_w == pytest.approx(8.0)
    assert result.efficiency == pytest.approx(0.8)
