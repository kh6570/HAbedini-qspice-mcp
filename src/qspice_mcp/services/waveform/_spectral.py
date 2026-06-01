"""Shared spectral-analysis helpers for waveform services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services._shared.paths import validate_time_window

if TYPE_CHECKING:
    from numpy.typing import NDArray

_MIN_SPECTRAL_POINTS = 2
_MIN_SAMPLES_PER_CYCLE = 16


@dataclass(frozen=True, slots=True)
class UniformWaveform:
    """One uniformly sampled waveform window."""

    x: NDArray[np.float64]
    y: NDArray[np.float64]
    sample_interval_s: float
    sample_count: int
    window_start_s: float
    window_end_s: float


@dataclass(frozen=True, slots=True)
class FftSpectrum:
    """One single-sided FFT spectrum."""

    frequency_hz: NDArray[np.float64]
    amplitude: NDArray[np.float64]
    magnitude_db: NDArray[np.float64]
    phase_deg: NDArray[np.float64]


def _validate_axis(axis: NDArray[np.float64]) -> None:
    if axis.shape[0] < _MIN_SPECTRAL_POINTS:
        raise ValueError("Spectral analysis requires at least two waveform samples.")
    if np.any(np.diff(axis) <= 0):
        raise ValueError("Spectral analysis requires a strictly increasing waveform axis.")


def prepare_uniform_waveform(
    axis: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    t_start: float | None = None,
    t_end: float | None = None,
    sample_count: int | None = None,
) -> UniformWaveform:
    """Resample one waveform window to a uniform time grid."""

    validate_time_window(t_start, t_end)
    _validate_axis(axis)
    start = float(axis[0] if t_start is None else t_start)
    end = float(axis[-1] if t_end is None else t_end)
    if end <= start:
        raise ValueError("The requested spectral window must have positive duration.")
    normalized_sample_count = sample_count if sample_count is not None else int(axis.shape[0])
    if normalized_sample_count < _MIN_SPECTRAL_POINTS:
        raise ValueError("Spectral analysis requires at least two resampled points.")
    if start < float(axis[0]) or end > float(axis[-1]):
        raise ValueError("Requested spectral window falls outside the available waveform axis.")

    resampled_axis = np.linspace(start, end, num=normalized_sample_count, endpoint=False)
    resampled_values = np.interp(resampled_axis, axis, values)
    sample_interval = (end - start) / float(normalized_sample_count)
    return UniformWaveform(
        x=np.asarray(resampled_axis, dtype=np.float64),
        y=np.asarray(resampled_values, dtype=np.float64),
        sample_interval_s=float(sample_interval),
        sample_count=int(normalized_sample_count),
        window_start_s=start,
        window_end_s=end,
    )


def prepare_period_window(
    axis: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    fundamental_hz: float,
    periods: int,
    t_end: float | None = None,
    samples_per_cycle: int = 512,
) -> UniformWaveform:
    """Resample a trailing integer-cycle window for harmonic analysis."""

    if fundamental_hz <= 0:
        raise ValueError("fundamental_hz must be positive.")
    if periods < 1:
        raise ValueError("periods must be at least 1.")
    if samples_per_cycle < _MIN_SAMPLES_PER_CYCLE:
        raise ValueError("samples_per_cycle must be at least 16.")
    resolved_t_end = float(axis[-1] if t_end is None else t_end)
    duration = periods / fundamental_hz
    resolved_t_start = resolved_t_end - duration
    return prepare_uniform_waveform(
        axis,
        values,
        t_start=resolved_t_start,
        t_end=resolved_t_end,
        sample_count=max(periods * samples_per_cycle, 256),
    )


def compute_single_sided_fft(
    waveform: UniformWaveform,
    *,
    remove_mean: bool = False,
) -> FftSpectrum:
    """Compute one single-sided FFT amplitude spectrum."""

    samples = waveform.y - np.mean(waveform.y) if remove_mean else waveform.y
    fft_values = np.fft.rfft(samples)
    amplitude = np.abs(fft_values) * (2.0 / waveform.sample_count)
    if amplitude.shape[0] > 0:
        amplitude[0] /= 2.0
    if waveform.sample_count % 2 == 0 and amplitude.shape[0] > 1:
        amplitude[-1] /= 2.0
    phase_deg = np.angle(fft_values, deg=True)
    frequency_hz = np.fft.rfftfreq(waveform.sample_count, d=waveform.sample_interval_s)
    magnitude_db = np.full(amplitude.shape, -np.inf, dtype=np.float64)
    mask = amplitude > 0
    magnitude_db[mask] = 20.0 * np.log10(amplitude[mask])
    return FftSpectrum(
        frequency_hz=np.asarray(frequency_hz, dtype=np.float64),
        amplitude=np.asarray(amplitude, dtype=np.float64),
        magnitude_db=np.asarray(magnitude_db, dtype=np.float64),
        phase_deg=np.asarray(phase_deg, dtype=np.float64),
    )


__all__ = [
    "FftSpectrum",
    "UniformWaveform",
    "compute_single_sided_fft",
    "prepare_period_window",
    "prepare_uniform_waveform",
]
