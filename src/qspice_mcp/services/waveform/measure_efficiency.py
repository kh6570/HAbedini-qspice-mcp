"""Service for average power-transfer efficiency over a transient window."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services._backends.waveform import load_waveform
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_MIN_EFFICIENCY_SAMPLES = 1


@dataclass(frozen=True, slots=True)
class EfficiencyMeasurement:
    """Average input/output power and efficiency over one transient window."""

    raw_path: Path
    plot_name: str | None
    input_power_signal: str
    output_power_signal: str
    step: int
    sample_count: int
    t_start: float
    t_end: float
    average_input_power_w: float
    average_output_power_w: float
    efficiency: float | None


SERVICE_SPEC = ServiceSpec(
    name="measure_efficiency",
    title="Measure Efficiency",
    summary=(
        "Compute average input power, output power, and Pout/Pin efficiency "
        "from transient power traces (for example SAVEPOWERS `p(...)` signals)."
    ),
    phase="implemented",
)


def measure_efficiency(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    input_power_signal: str,
    output_power_signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    t_start: float | None = None,
    t_end: float | None = None,
) -> EfficiencyMeasurement:
    """Compute average power efficiency from two transient power traces."""

    normalized_workspace = workspace_root.resolve(strict=False)
    input_waveform = load_waveform(
        raw_path,
        workspace_root=normalized_workspace,
        signal=input_power_signal,
        step=step,
        step_filters=step_filters,
        t_start=t_start,
        t_end=t_end,
    )
    output_waveform = load_waveform(
        raw_path,
        workspace_root=normalized_workspace,
        signal=output_power_signal,
        step=input_waveform.step,
        step_filters=step_filters,
        t_start=t_start,
        t_end=t_end,
    )
    if input_waveform.x_unit != "s" or output_waveform.x_unit != "s":
        raise ValueError(
            "Efficiency measurement requires transient waveforms with a time axis."
        )
    if input_waveform.y.shape[0] < _MIN_EFFICIENCY_SAMPLES:
        raise ValueError("Efficiency measurement requires at least one sample.")

    average_input_power_w = float(np.mean(np.abs(input_waveform.y)))
    average_output_power_w = float(np.mean(np.abs(output_waveform.y)))
    efficiency: float | None = None
    if average_input_power_w > 0.0:
        efficiency = average_output_power_w / average_input_power_w

    return EfficiencyMeasurement(
        raw_path=input_waveform.raw_path,
        plot_name=input_waveform.plot_name,
        input_power_signal=input_waveform.signal,
        output_power_signal=output_waveform.signal,
        step=input_waveform.step,
        sample_count=int(input_waveform.y.shape[0]),
        t_start=float(input_waveform.x[0]),
        t_end=float(input_waveform.x[-1]),
        average_input_power_w=average_input_power_w,
        average_output_power_w=average_output_power_w,
        efficiency=efficiency,
    )


__all__ = ["SERVICE_SPEC", "EfficiencyMeasurement", "measure_efficiency"]
