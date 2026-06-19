"""Tests for stability margin extraction."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

from qspice_mcp.services.waveform.measure_stability_margins import measure_stability_margins

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
BODE_RAW_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "qraw" / "bode-only.qraw"
BODE_LOG_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "qraw" / "bode-only.log"


class FakeLoopGainRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([10.0, 100.0, 1000.0, 10000.0], dtype=np.float64)
        magnitudes = np.array([10.0, 3.16227766, 1.0, 0.1], dtype=np.float64)
        phases = np.deg2rad(np.array([-10.0, -45.0, -120.0, -200.0], dtype=np.float64))
        self._wave = magnitudes * np.exp(1j * phases)

    def get_trace_names(self) -> list[str]:
        return ["frequency", "V(loop)"]

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
        if trace_ref == "frequency":
            return self._axis
        return self._wave

    def get_plot_name(self) -> str:
        return "AC Analysis"


def test_measure_stability_margins_finds_crossovers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeLoopGainRawRead, "fake-backend")
    )

    result = measure_stability_margins(
        raw_path,
        workspace_root=tmp_path,
        signal="V(loop)",
    )

    assert result.gain_crossover_hz == pytest.approx(1000.0, rel=0.05)
    assert result.phase_margin_deg == pytest.approx(60.0, rel=0.05)
    assert result.phase_crossover_hz == pytest.approx(5623.4132519, rel=0.05)
    assert result.gain_margin_db == pytest.approx(15.0, rel=0.05)
    assert result.stable_at_unity is True


def test_measure_stability_margins_reads_external_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    log_path = tmp_path / BODE_LOG_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)
    copy2(BODE_LOG_FIXTURE, log_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = measure_stability_margins(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
    )

    assert result.plot_name == "AC Analysis"
    assert result.sample_count == 5220
    assert result.gain_crossover_hz is not None
    assert result.phase_margin_deg is not None
