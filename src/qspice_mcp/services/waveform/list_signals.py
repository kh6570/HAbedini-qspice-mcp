"""Service for listing available waveform signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from qspice_mcp.services._backends.waveform import (
    get_axis_name,
    get_signal_names,
    get_step_indices,
    infer_axis_unit,
    infer_signal_unit,
    open_raw_reader,
    read_axis_array,
    resolve_step_request,
    to_wave_array,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SignalSummary:
    """Metadata for one waveform signal available in a raw file."""

    name: str
    point_count: int
    complex_data: bool
    unit: str


@dataclass(frozen=True, slots=True)
class SignalCatalog:
    """Signal inventory for one QSpice `.qraw` artifact."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    axis_unit: str
    resolved_step: int
    step_count: int
    point_count: int
    signal_count: int
    signals: tuple[SignalSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="list_signals",
    title="List Signals",
    summary="Enumerate available signals and point counts from a QSpice result file.",
    phase="implemented",
)


def list_signals(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
) -> SignalCatalog:
    """Enumerate the available waveform signals in one `.qraw` file."""

    normalized_workspace = workspace_root.resolve(strict=False)
    reader, resolved_path = open_raw_reader(raw_path, workspace_root=normalized_workspace)
    plot_name = reader.get_plot_name() if hasattr(reader, "get_plot_name") else None
    axis_name = get_axis_name(reader)
    axis_unit = infer_axis_unit(axis_name)
    step_indices = get_step_indices(reader)
    resolved_step = resolve_step_request(
        reader,
        raw_path=resolved_path,
        workspace_root=normalized_workspace,
        step=step,
        step_filters=step_filters,
    )
    signal_names = get_signal_names(reader)
    warnings: list[str] = []

    point_count = 0
    if axis_name is not None:
        point_count = int(read_axis_array(reader, step=resolved_step).shape[0])

    signals: list[SignalSummary] = []
    for signal_name in signal_names:
        complex_data = bool(plot_name and plot_name.strip().lower().startswith(("ac", "noise")))
        signal_point_count = point_count
        try:
            wave = to_wave_array(reader.get_wave(signal_name, step=resolved_step))
        except Exception:
            warnings.append(
                f"Could not materialize waveform metadata for alias-like signal "
                f"'{signal_name}'; returned heuristic metadata instead."
            )
        else:
            complex_data = bool(np.iscomplexobj(wave))
            signal_point_count = int(wave.shape[0])
            if point_count == 0:
                point_count = signal_point_count
        signals.append(
            SignalSummary(
                name=signal_name,
                point_count=signal_point_count,
                complex_data=complex_data,
                unit=infer_signal_unit(signal_name, "magnitude" if complex_data else "real"),
            )
        )

    return SignalCatalog(
        raw_path=resolved_path,
        plot_name=plot_name,
        axis_name=axis_name,
        axis_unit=axis_unit,
        resolved_step=resolved_step,
        step_count=len(step_indices),
        point_count=point_count,
        signal_count=len(signals),
        signals=tuple(signals),
        warnings=tuple(warnings),
    )


__all__ = ["SERVICE_SPEC", "SignalCatalog", "SignalSummary", "list_signals"]
