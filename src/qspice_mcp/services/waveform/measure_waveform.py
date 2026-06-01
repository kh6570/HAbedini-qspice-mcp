"""Service for scalar waveform measurements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

import numpy as np

from qspice_mcp.services._backends.waveform import WaveformComponent, load_waveform
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

MeasurementOperation = Literal[
    "min",
    "max",
    "mean",
    "rms",
    "peak_to_peak",
    "abs_max",
    "start",
    "end",
    "integral",
]
_MIN_INTEGRAL_POINTS = 2


@dataclass(frozen=True, slots=True)
class WaveformMeasurement:
    """One scalar measurement extracted from a waveform."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    component: str
    operation: str
    sample_count: int
    x_unit: str
    y_unit: str
    value: float


SERVICE_SPEC = ServiceSpec(
    name="measure_waveform",
    title="Measure Waveform",
    summary="Compute scalar measurements such as extrema, RMS, and crossing times.",
    phase="implemented",
)


def _rms_value(y_values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y_values))))


def _peak_to_peak_value(y_values: np.ndarray) -> float:
    return float(np.max(y_values) - np.min(y_values))


_SIMPLE_MEASUREMENTS: dict[str, Callable[[np.ndarray], float]] = {
    "min": lambda y_values: float(np.min(y_values)),
    "max": lambda y_values: float(np.max(y_values)),
    "mean": lambda y_values: float(np.mean(y_values)),
    "rms": _rms_value,
    "peak_to_peak": _peak_to_peak_value,
    "abs_max": lambda y_values: float(np.max(np.abs(y_values))),
}


def _measure(operation: str, x_values: np.ndarray, y_values: np.ndarray) -> float:
    """Compute one scalar measurement over a real-valued waveform."""

    normalized_operation = operation.lower()
    simple_measurement = _SIMPLE_MEASUREMENTS.get(normalized_operation)
    if simple_measurement is not None:
        return simple_measurement(y_values)
    if normalized_operation == "start":
        return float(y_values[0])
    if normalized_operation == "end":
        return float(y_values[-1])
    if normalized_operation == "integral":
        if y_values.shape[0] < _MIN_INTEGRAL_POINTS:
            return 0.0
        return float(np.trapezoid(y_values, x_values))
    raise ValueError(f"Unsupported waveform measurement operation: {operation}")


def measure_waveform(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    operation: MeasurementOperation,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> WaveformMeasurement:
    """Compute one scalar measurement over a selected waveform component."""

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
    return WaveformMeasurement(
        raw_path=waveform.raw_path,
        plot_name=waveform.plot_name,
        axis_name=waveform.axis_name,
        signal=waveform.signal,
        step=waveform.step,
        component=waveform.component,
        operation=operation.lower(),
        sample_count=int(waveform.y.shape[0]),
        x_unit=waveform.x_unit,
        y_unit=waveform.y_unit,
        value=_measure(operation, waveform.x, waveform.y),
    )


__all__ = ["SERVICE_SPEC", "MeasurementOperation", "WaveformMeasurement", "measure_waveform"]
