"""Service for time-domain step-response metrics on transient waveforms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services._backends.waveform import WaveformComponent, load_waveform
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_MIN_STEP_SAMPLES = 2
_DEFAULT_SETTLING_BAND_PCT = 2.0


@dataclass(frozen=True, slots=True)
class StepResponseMeasurement:
    """Classic step-response metrics extracted from one transient trace."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    sample_count: int
    x_unit: str
    y_unit: str
    initial_value: float
    final_value: float
    rise_time_s: float | None
    delay_time_s: float | None
    overshoot_pct: float | None
    settling_time_s: float | None
    peak_value: float


SERVICE_SPEC = ServiceSpec(
    name="measure_step_response",
    title="Measure Step Response",
    summary=(
        "Compute rise time, delay, overshoot, and settling time from one transient waveform trace."
    ),
    phase="implemented",
)


def _estimate_endpoint(values: np.ndarray, *, tail: bool) -> float:
    sample_count = values.shape[0]
    if sample_count == 0:
        raise ValueError("Step response measurement requires at least one sample.")
    window = max(1, sample_count // 10)
    segment = values[-window:] if tail else values[:window]
    return float(np.mean(segment))


def _interpolate_crossing_time(
    axis: np.ndarray,
    values: np.ndarray,
    *,
    threshold: float,
    rising: bool,
) -> float | None:
    for index in range(values.shape[0] - 1):
        value_a = values[index]
        value_b = values[index + 1]
        if value_a == threshold:
            return float(axis[index])
        if rising:
            if value_a < threshold <= value_b:
                fraction = (threshold - value_a) / (value_b - value_a)
                return float(axis[index] + fraction * (axis[index + 1] - axis[index]))
        elif value_a > threshold >= value_b:
            fraction = (threshold - value_a) / (value_b - value_a)
            return float(axis[index] + fraction * (axis[index + 1] - axis[index]))
    return None


def _compute_settling_time(
    axis: np.ndarray,
    values: np.ndarray,
    *,
    final_value: float,
    step_span: float,
    settling_band_pct: float,
    step_start_time: float,
) -> float | None:
    band = abs(step_span) * (settling_band_pct / 100.0)
    if band == 0.0:
        band = abs(final_value) * (settling_band_pct / 100.0)
    if band == 0.0:
        return None
    lower = final_value - band
    upper = final_value + band
    settled_index: int | None = None
    for index in range(values.shape[0]):
        if not (lower <= values[index] <= upper):
            continue
        if np.all((values[index:] >= lower) & (values[index:] <= upper)):
            settled_index = index
            break
    if settled_index is None:
        return None
    return float(axis[settled_index] - step_start_time)


def measure_step_response(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
    initial_value: float | None = None,
    final_value: float | None = None,
    lower_pct: float = 10.0,
    upper_pct: float = 90.0,
    settling_band_pct: float = _DEFAULT_SETTLING_BAND_PCT,
) -> StepResponseMeasurement:
    """Compute step-response metrics from one transient waveform trace."""

    waveform = load_waveform(
        raw_path,
        workspace_root=workspace_root.resolve(strict=False),
        signal=signal,
        step=step,
        step_filters=step_filters,
        component=component,
        t_start=t_start,
        t_end=t_end,
    )
    if waveform.x_unit != "s":
        raise ValueError(
            "Step response measurement requires a transient waveform with a time axis."
        )
    if waveform.y.shape[0] < _MIN_STEP_SAMPLES:
        raise ValueError("Step response measurement requires at least two samples.")

    axis = np.asarray(waveform.x, dtype=np.float64)
    values = np.asarray(waveform.y, dtype=np.float64)
    resolved_initial = (
        float(initial_value)
        if initial_value is not None
        else _estimate_endpoint(values, tail=False)
    )
    resolved_final = (
        float(final_value) if final_value is not None else _estimate_endpoint(values, tail=True)
    )
    step_span = resolved_final - resolved_initial
    if abs(step_span) < np.finfo(np.float64).eps:
        raise ValueError("Step response measurement requires distinct initial and final values.")

    rising = step_span > 0.0
    lower_threshold = resolved_initial + (lower_pct / 100.0) * step_span
    upper_threshold = resolved_initial + (upper_pct / 100.0) * step_span
    midpoint_threshold = resolved_initial + 0.5 * step_span

    lower_time = _interpolate_crossing_time(
        axis,
        values,
        threshold=lower_threshold,
        rising=rising,
    )
    upper_time = _interpolate_crossing_time(
        axis,
        values,
        threshold=upper_threshold,
        rising=rising,
    )
    rise_time_s = (
        float(upper_time - lower_time)
        if lower_time is not None and upper_time is not None
        else None
    )
    delay_time_s = _interpolate_crossing_time(
        axis,
        values,
        threshold=midpoint_threshold,
        rising=rising,
    )

    peak_value = float(np.max(values) if rising else np.min(values))
    overshoot_pct: float | None = None
    if rising and peak_value > resolved_final:
        overshoot_pct = ((peak_value - resolved_final) / abs(step_span)) * 100.0
    elif not rising and peak_value < resolved_final:
        overshoot_pct = ((resolved_final - peak_value) / abs(step_span)) * 100.0

    step_start_time = float(axis[0])
    settling_time_s = _compute_settling_time(
        axis,
        values,
        final_value=resolved_final,
        step_span=step_span,
        settling_band_pct=settling_band_pct,
        step_start_time=step_start_time,
    )

    return StepResponseMeasurement(
        raw_path=waveform.raw_path,
        plot_name=waveform.plot_name,
        axis_name=waveform.axis_name,
        signal=waveform.signal,
        step=waveform.step,
        sample_count=int(values.shape[0]),
        x_unit=waveform.x_unit,
        y_unit=waveform.y_unit,
        initial_value=resolved_initial,
        final_value=resolved_final,
        rise_time_s=rise_time_s,
        delay_time_s=delay_time_s,
        overshoot_pct=overshoot_pct,
        settling_time_s=settling_time_s,
        peak_value=peak_value,
    )


__all__ = ["SERVICE_SPEC", "StepResponseMeasurement", "measure_step_response"]
