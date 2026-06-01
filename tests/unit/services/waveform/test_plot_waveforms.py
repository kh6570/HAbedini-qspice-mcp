"""Tests for the RawRead-backed plot_waveforms service."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import numpy as np
import pytest

from qspice_mcp.services.waveform.plot_waveforms import plot_waveforms

if TYPE_CHECKING:
    from pathlib import Path

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")


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
        }

    def get_trace_names(self) -> list[str]:
        return ["time", *self._waves.keys()]

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


def test_plot_waveforms_creates_png_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = plot_waveforms(
        raw_path,
        workspace_root=tmp_path,
        signals=("V(out)", "I(L1)"),
        output_path=tmp_path / "plots" / "demo.png",
        max_points=4,
    )

    assert result.raw_path == raw_path.resolve(strict=False)
    assert result.plot_path == (tmp_path / "plots" / "demo.png").resolve(strict=False)
    assert result.plot_path.is_file()
    assert result.format == "png"
    assert result.signal_count == 2
    assert result.point_count == 4
    assert result.downsampled is True
    assert result.plot_path.stat().st_size > 0


def test_plot_waveforms_rejects_mismatched_output_suffix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    with pytest.raises(ValueError, match=r"\.png"):
        plot_waveforms(
            raw_path,
            workspace_root=tmp_path,
            signals=("V(out)",),
            output_path=tmp_path / "plots" / "demo.txt",
            fmt="png",
        )
