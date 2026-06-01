"""Service for bounded waveform reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.budgets import DEFAULT_BUDGET
from qspice_mcp.core.exceptions import BudgetExceededError
from qspice_mcp.services._backends.waveform import (
    WaveformComponent,
    apply_budget,
    build_budget,
    load_waveform,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class WaveformRead:
    """One bounded waveform read, ready for JSON serialization."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    component: str
    x_unit: str
    y_unit: str
    point_count: int
    original_point_count: int
    downsampled: bool
    complex_source: bool
    x_values: tuple[float, ...]
    y_values: tuple[float, ...]


SERVICE_SPEC = ServiceSpec(
    name="read_waveform",
    title="Read Waveform",
    summary="Read one waveform trace with time-window filtering and data budgeting.",
    phase="implemented",
)


def _validate_waveform_response_budget(
    *,
    max_points: int | None,
    max_bytes: int | None,
) -> None:
    if max_points is not None and max_points > DEFAULT_BUDGET.max_points:
        raise BudgetExceededError(
            "read_waveform responses are capped at "
            f"{DEFAULT_BUDGET.max_points} points; use plot_waveforms, "
            "export_waveform_csv, or export_derived_raw for larger outputs."
        )
    if max_bytes is not None and max_bytes > DEFAULT_BUDGET.max_bytes:
        raise BudgetExceededError(
            "read_waveform responses are capped at "
            f"{DEFAULT_BUDGET.max_bytes} bytes; use plot_waveforms, "
            "export_waveform_csv, or export_derived_raw for larger outputs."
        )


def read_waveform(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
    max_points: int | None = None,
    max_bytes: int | None = None,
) -> WaveformRead:
    """Read one waveform trace with axis-window filtering and output budgeting."""

    _validate_waveform_response_budget(max_points=max_points, max_bytes=max_bytes)

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
    original_point_count = int(waveform.x.shape[0])
    bounded_x, bounded_y, downsampled = apply_budget(
        waveform.x,
        waveform.y,
        budget=build_budget(max_points=max_points, max_bytes=max_bytes),
    )
    return WaveformRead(
        raw_path=waveform.raw_path,
        plot_name=waveform.plot_name,
        axis_name=waveform.axis_name,
        signal=waveform.signal,
        step=waveform.step,
        component=waveform.component,
        x_unit=waveform.x_unit,
        y_unit=waveform.y_unit,
        point_count=int(bounded_x.shape[0]),
        original_point_count=original_point_count,
        downsampled=downsampled,
        complex_source=waveform.complex_source,
        x_values=tuple(float(value) for value in bounded_x.tolist()),
        y_values=tuple(float(value) for value in bounded_y.tolist()),
    )


__all__ = ["SERVICE_SPEC", "WaveformRead", "read_waveform"]
