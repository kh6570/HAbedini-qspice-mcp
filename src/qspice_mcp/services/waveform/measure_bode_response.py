"""Service for sampling magnitude and phase from frequency-domain waveform data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services._backends.waveform import (
    get_axis_name,
    get_plot_name,
    has_axis,
    infer_axis_unit,
    open_raw_reader,
    read_axis_array,
    resolve_signal_name,
    resolve_step_request,
    to_wave_array,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from numpy.typing import NDArray

_MIN_BODE_SAMPLES = 2


@dataclass(frozen=True, slots=True)
class BodeSample:
    """Interpolated Bode response data at one requested frequency."""

    frequency_hz: float
    magnitude_db: float
    phase_deg: float
    real: float
    imag: float


@dataclass(frozen=True, slots=True)
class BodeMeasurement:
    """Interpolated Bode response extracted from one frequency-domain trace."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    sample_count: int
    interpolation: str
    samples: tuple[BodeSample, ...]


SERVICE_SPEC = ServiceSpec(
    name="measure_bode_response",
    title="Measure Bode Response",
    summary=(
        "Sample magnitude and phase from one frequency-domain waveform trace "
        "at requested frequencies."
    ),
    phase="implemented",
)


def _prepare_interpolation_axis(
    axis: NDArray[np.float64],
    *,
    frequencies_hz: tuple[float, ...],
) -> tuple[NDArray[np.float64], NDArray[np.float64], str]:
    if np.any(axis <= 0) or any(frequency <= 0 for frequency in frequencies_hz):
        return axis, np.asarray(frequencies_hz, dtype=np.float64), "linear"
    return np.log10(axis), np.log10(np.asarray(frequencies_hz, dtype=np.float64)), "log"


def _sorted_unique_series(
    axis: NDArray[np.float64],
    values: NDArray[np.complex128],
) -> tuple[NDArray[np.float64], NDArray[np.complex128]]:
    indices = np.argsort(axis)
    sorted_axis = axis[indices]
    sorted_values = values[indices]
    unique_axis, unique_indices = np.unique(sorted_axis, return_index=True)
    if unique_axis.shape[0] < _MIN_BODE_SAMPLES:
        raise ValueError("Bode measurement requires at least two unique frequency samples.")
    return unique_axis, sorted_values[unique_indices]


def measure_bode_response(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    frequencies_hz: tuple[float, ...] | list[float],
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
) -> BodeMeasurement:
    """Measure magnitude and phase at selected frequencies from one AC-style waveform trace."""

    normalized_frequencies = tuple(float(value) for value in frequencies_hz)
    if not normalized_frequencies:
        raise ValueError("frequencies_hz must contain at least one frequency.")

    reader, resolved_path = open_raw_reader(
        raw_path, workspace_root=workspace_root.resolve(strict=False)
    )
    normalized_step = resolve_step_request(
        reader,
        raw_path=resolved_path,
        workspace_root=workspace_root.resolve(strict=False),
        step=step,
        step_filters=step_filters,
    )
    resolved_signal = resolve_signal_name(reader, signal)
    raw_wave = np.asarray(to_wave_array(reader.get_wave(resolved_signal, step=normalized_step)))
    axis_name = get_axis_name(reader) if has_axis(reader) else None
    axis = (
        read_axis_array(reader, step=normalized_step)
        if has_axis(reader)
        else np.arange(raw_wave.shape[0], dtype=np.float64)
    )
    if infer_axis_unit(axis_name) != "Hz":
        raise ValueError(
            "Bode measurement requires frequency-domain waveform data with a frequency axis."
        )

    complex_values = np.asarray(raw_wave, dtype=np.complex128)
    unique_axis, unique_values = _sorted_unique_series(axis, complex_values)
    magnitude_db = np.full(unique_values.shape, -np.inf, dtype=np.float64)
    magnitudes = np.abs(unique_values)
    non_zero = magnitudes > 0
    magnitude_db[non_zero] = 20.0 * np.log10(magnitudes[non_zero])
    phase_deg = np.angle(unique_values, deg=True)
    interpolation_axis, target_axis, interpolation = _prepare_interpolation_axis(
        unique_axis,
        frequencies_hz=normalized_frequencies,
    )
    real_values = np.real(unique_values)
    imag_values = np.imag(unique_values)

    interpolated_magnitude = np.interp(target_axis, interpolation_axis, magnitude_db)
    interpolated_phase = np.interp(target_axis, interpolation_axis, phase_deg)
    interpolated_real = np.interp(target_axis, interpolation_axis, real_values)
    interpolated_imag = np.interp(target_axis, interpolation_axis, imag_values)

    samples = tuple(
        BodeSample(
            frequency_hz=frequency,
            magnitude_db=float(interpolated_magnitude[index]),
            phase_deg=float(interpolated_phase[index]),
            real=float(interpolated_real[index]),
            imag=float(interpolated_imag[index]),
        )
        for index, frequency in enumerate(normalized_frequencies)
    )
    return BodeMeasurement(
        raw_path=resolved_path,
        plot_name=get_plot_name(reader),
        axis_name=axis_name,
        signal=resolved_signal,
        step=normalized_step,
        sample_count=int(unique_axis.shape[0]),
        interpolation=interpolation,
        samples=samples,
    )


__all__ = ["SERVICE_SPEC", "BodeMeasurement", "BodeSample", "measure_bode_response"]
