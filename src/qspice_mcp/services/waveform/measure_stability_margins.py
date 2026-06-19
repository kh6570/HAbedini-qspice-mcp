"""Service for computing phase and gain margins from a loop-gain Bode trace."""

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
class StabilityMargins:
    """Phase and gain margins extracted from one loop-gain frequency sweep."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    sample_count: int
    gain_crossover_hz: float | None
    phase_margin_deg: float | None
    phase_crossover_hz: float | None
    gain_margin_db: float | None
    stable_at_unity: bool | None


SERVICE_SPEC = ServiceSpec(
    name="measure_stability_margins",
    title="Measure Stability Margins",
    summary=(
        "Compute crossover frequency, phase margin, and gain margin from one "
        "loop-gain frequency-domain waveform trace."
    ),
    phase="implemented",
)


def _sorted_unique_series(
    axis: NDArray[np.float64],
    values: NDArray[np.complex128],
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    indices = np.argsort(axis)
    sorted_axis = axis[indices]
    sorted_values = values[indices]
    unique_axis, unique_indices = np.unique(sorted_axis, return_index=True)
    if unique_axis.shape[0] < _MIN_BODE_SAMPLES:
        raise ValueError("Stability margin measurement requires at least two frequency samples.")
    unique_values = sorted_values[unique_indices]
    magnitudes = np.abs(unique_values)
    magnitude_db = np.full(unique_values.shape, -np.inf, dtype=np.float64)
    non_zero = magnitudes > 0
    magnitude_db[non_zero] = 20.0 * np.log10(magnitudes[non_zero])
    phase_deg = np.rad2deg(np.unwrap(np.angle(unique_values)))
    return unique_axis, magnitude_db, phase_deg


def _interpolation_axis(axis: NDArray[np.float64]) -> NDArray[np.float64]:
    if np.all(axis > 0):
        return np.log10(axis)
    return axis


def _interpolate_crossing(
    axis: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    target: float,
) -> float | None:
    interpolation_axis = _interpolation_axis(axis)
    for index in range(values.shape[0] - 1):
        value_a = values[index]
        value_b = values[index + 1]
        if value_a == target:
            return float(axis[index])
        if (value_a - target) * (value_b - target) > 0:
            continue
        fraction = (target - value_a) / (value_b - value_a)
        interpolated_axis = interpolation_axis[index] + fraction * (
            interpolation_axis[index + 1] - interpolation_axis[index]
        )
        if np.all(axis > 0):
            return float(10.0**interpolated_axis)
        return float(
            axis[index] + fraction * (axis[index + 1] - axis[index]),
        )
    return None


def _find_gain_crossover(
    axis: NDArray[np.float64],
    magnitude_db: NDArray[np.float64],
) -> float | None:
    for index in range(magnitude_db.shape[0] - 1):
        magnitude_a = magnitude_db[index]
        magnitude_b = magnitude_db[index + 1]
        if magnitude_a == 0.0:
            return float(axis[index])
        if magnitude_a > 0.0 >= magnitude_b:
            return _interpolate_crossing(
                axis[index : index + 2],
                magnitude_db[index : index + 2],
                target=0.0,
            )
        if magnitude_b > 0.0 >= magnitude_a:
            return _interpolate_crossing(
                axis[index : index + 2],
                magnitude_db[index : index + 2],
                target=0.0,
            )
    return None


def _find_phase_crossover(
    axis: NDArray[np.float64],
    phase_deg: NDArray[np.float64],
) -> float | None:
    target = -180.0
    for index in range(phase_deg.shape[0] - 1):
        phase_a = phase_deg[index]
        phase_b = phase_deg[index + 1]
        if phase_a == target:
            return float(axis[index])
        if (phase_a - target) * (phase_b - target) > 0:
            continue
        return _interpolate_crossing(
            axis[index : index + 2],
            phase_deg[index : index + 2],
            target=target,
        )
    return None


def _interpolate_value_at_frequency(
    axis: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    frequency_hz: float,
) -> float:
    interpolation_axis = _interpolation_axis(axis)
    target_axis = np.log10(frequency_hz) if np.all(axis > 0) else frequency_hz
    return float(np.interp(target_axis, interpolation_axis, values))


def measure_stability_margins(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
) -> StabilityMargins:
    """Compute phase and gain margins from one loop-gain frequency sweep."""

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
            "Stability margin measurement requires frequency-domain waveform data "
            "with a frequency axis."
        )

    unique_axis, magnitude_db, phase_deg = _sorted_unique_series(
        np.asarray(axis, dtype=np.float64),
        np.asarray(raw_wave, dtype=np.complex128),
    )
    gain_crossover_hz = _find_gain_crossover(unique_axis, magnitude_db)
    phase_crossover_hz = _find_phase_crossover(unique_axis, phase_deg)

    phase_margin_deg: float | None = None
    if gain_crossover_hz is not None:
        phase_at_gain_crossover = _interpolate_value_at_frequency(
            unique_axis,
            phase_deg,
            frequency_hz=gain_crossover_hz,
        )
        phase_margin_deg = 180.0 + phase_at_gain_crossover

    gain_margin_db: float | None = None
    if phase_crossover_hz is not None:
        gain_at_phase_crossover = _interpolate_value_at_frequency(
            unique_axis,
            magnitude_db,
            frequency_hz=phase_crossover_hz,
        )
        gain_margin_db = -gain_at_phase_crossover

    stable_at_unity: bool | None = None
    if phase_margin_deg is not None:
        stable_at_unity = phase_margin_deg > 0.0

    return StabilityMargins(
        raw_path=resolved_path,
        plot_name=get_plot_name(reader),
        axis_name=axis_name,
        signal=resolved_signal,
        step=normalized_step,
        sample_count=int(unique_axis.shape[0]),
        gain_crossover_hz=gain_crossover_hz,
        phase_margin_deg=phase_margin_deg,
        phase_crossover_hz=phase_crossover_hz,
        gain_margin_db=gain_margin_db,
        stable_at_unity=stable_at_unity,
    )


__all__ = ["SERVICE_SPEC", "StabilityMargins", "measure_stability_margins"]
