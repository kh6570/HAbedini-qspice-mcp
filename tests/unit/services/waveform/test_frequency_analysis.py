"""Tests for Phase 10 waveform analysis services."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

from qspice_mcp.services._backends.waveform import LoadedWaveform
from qspice_mcp.services.waveform.compute_thd import compute_thd
from qspice_mcp.services.waveform.export_fft_spectrum import export_fft_spectrum
from qspice_mcp.services.waveform.measure_bode_response import measure_bode_response

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
compute_thd_module = importlib.import_module("qspice_mcp.services.waveform.compute_thd")
export_fft_module = importlib.import_module("qspice_mcp.services.waveform.export_fft_spectrum")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
BODE_RAW_FIXTURE = FIXTURE_ROOT / "bode-only.qraw"
BODE_LOG_FIXTURE = FIXTURE_ROOT / "bode-only.log"


class FakeAcRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([10.0, 100.0, 1000.0], dtype=np.float64)
        self._wave = np.array([10.0 + 0.0j, 1.0 - 1.0j, 0.1 - 0.1j], dtype=np.complex128)

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


def _demo_time_waveform(raw_path: Path) -> LoadedWaveform:
    axis = np.linspace(0.0, 0.1, num=20001, dtype=np.float64)
    values = np.sin(2.0 * np.pi * 50.0 * axis) + 0.1 * np.sin(2.0 * np.pi * 100.0 * axis)
    return LoadedWaveform(
        raw_path=raw_path.resolve(strict=False),
        plot_name="Transient Analysis",
        axis_name="time",
        signal="V(out)",
        step=0,
        component="real",
        x=axis,
        y=np.asarray(values, dtype=np.float64),
        complex_source=False,
        x_unit="s",
        y_unit="V",
    )


def test_measure_bode_response_samples_complex_trace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeAcRawRead, "fake-backend")
    )

    result = measure_bode_response(
        raw_path,
        workspace_root=tmp_path,
        signal="V(loop)",
        frequencies_hz=[10.0, 1000.0],
    )

    assert result.interpolation == "log"
    assert result.samples[0].magnitude_db == pytest.approx(20.0)
    assert result.samples[1].phase_deg == pytest.approx(-45.0)


def test_measure_bode_response_reads_external_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    log_path = tmp_path / BODE_LOG_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)
    copy2(BODE_LOG_FIXTURE, log_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = measure_bode_response(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        frequencies_hz=[10.0, 1000.0],
    )

    assert result.plot_name == "AC Analysis"
    assert result.axis_name == "Frequency"
    assert result.interpolation == "log"
    assert result.sample_count == 5220
    assert result.samples[0].magnitude_db == pytest.approx(-15.483295944956936)
    assert result.samples[0].phase_deg == pytest.approx(-178.37190582939897)
    assert result.samples[1].magnitude_db == pytest.approx(-15.133507490084524)
    assert result.samples[1].phase_deg == pytest.approx(-163.81565164611413)


def test_compute_thd_estimates_second_harmonic_content(monkeypatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    waveform = _demo_time_waveform(raw_path)
    monkeypatch.setattr(compute_thd_module, "load_waveform", lambda *args, **kwargs: waveform)

    result = compute_thd(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        fundamental_hz=50.0,
        periods=5,
        harmonics=4,
    )

    assert result.thd_percent == pytest.approx(10.0, rel=0.05)
    assert result.contributions[1].harmonic == 2
    assert result.contributions[1].percent_of_fundamental == pytest.approx(10.0, rel=0.05)


def test_export_fft_spectrum_writes_csv(monkeypatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    waveform = _demo_time_waveform(raw_path)
    monkeypatch.setattr(export_fft_module, "load_waveform", lambda *args, **kwargs: waveform)
    destination = tmp_path / "fft.csv"

    result = export_fft_spectrum(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        sample_count=4096,
        output_path=destination,
    )

    lines = destination.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "frequency_hz,amplitude,magnitude_db,phase_deg"
    assert result.bin_count > 100
    fundamental_row = next(line for line in lines[1:] if line.startswith("50,"))
    assert float(fundamental_row.split(",")[1]) == pytest.approx(1.0, rel=0.05)
