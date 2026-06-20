"""Service for waveform plot generation."""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

from typing import TYPE_CHECKING

from matplotlib import pyplot as plt

from qspice_mcp.services._backends.waveform import (
    WaveformComponent,
    apply_budget,
    build_budget,
    load_waveform,
)
from qspice_mcp.services._shared.paths import resolve_workspace_output_path
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class WaveformPlot:
    """One derived plot artifact for one or more waveform traces."""

    raw_path: Path
    plot_path: Path
    format: str
    title: str
    signals: tuple[str, ...]
    step: int
    component: str
    signal_count: int
    point_count: int
    downsampled: bool
    x_unit: str
    y_unit: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="plot_waveforms",
    title="Plot Waveforms",
    summary="Generate derived plot artifacts for one or more QSpice signals.",
    read_only=False,
    phase="implemented",
    idempotent=True,
)


def _resolve_plot_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    raw_path: Path,
    fmt: str,
) -> Path:
    """Resolve an optional plot output path inside the workspace root."""

    return resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=raw_path.with_name(f"{raw_path.stem}-plot.{fmt}"),
        suffixes=(f".{fmt}",),
    )


def plot_waveforms(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signals: tuple[str, ...] | list[str],
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
    max_points: int | None = None,
    max_bytes: int | None = None,
    output_path: str | Path | None = None,
    fmt: str = "png",
    title: str | None = None,
) -> WaveformPlot:
    """Render one derived plot artifact for one or more waveform traces."""

    normalized_workspace = workspace_root.resolve(strict=False)
    normalized_signals = tuple(signals)
    if not normalized_signals:
        raise ValueError("At least one signal is required to generate a waveform plot.")

    normalized_format = fmt.lower()
    if normalized_format not in {"png", "svg"}:
        raise ValueError(f"Unsupported plot format: {fmt}")

    budget = build_budget(max_points=max_points, max_bytes=max_bytes)
    loaded_waveforms = [
        load_waveform(
            raw_path,
            workspace_root=normalized_workspace,
            signal=signal,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        for signal in normalized_signals
    ]
    plot_path = _resolve_plot_path(
        output_path,
        workspace_root=normalized_workspace,
        raw_path=loaded_waveforms[0].raw_path,
        fmt=normalized_format,
    )

    warnings: list[str] = []
    y_units = {waveform.y_unit for waveform in loaded_waveforms}
    if len(y_units) > 1:
        warnings.append("Signals use different inferred units; the shared y-axis label is generic.")

    figure, axes = plt.subplots(figsize=(10.0, 5.5), constrained_layout=True)
    downsampled_any = False
    point_count = 0
    effective_component = loaded_waveforms[0].component
    effective_title = title or loaded_waveforms[0].plot_name or "Waveform Plot"

    for waveform in loaded_waveforms:
        bounded_x, bounded_y, downsampled = apply_budget(waveform.x, waveform.y, budget=budget)
        downsampled_any = downsampled_any or downsampled
        point_count = max(point_count, int(bounded_x.shape[0]))
        axes.plot(bounded_x, bounded_y, linewidth=1.5, label=waveform.signal)

    axes.set_title(effective_title)
    axes.set_xlabel(f"{loaded_waveforms[0].axis_name or 'index'} [{loaded_waveforms[0].x_unit}]")
    if len(y_units) == 1:
        axes.set_ylabel(f"{effective_component} [{loaded_waveforms[0].y_unit}]")
    else:
        axes.set_ylabel(effective_component)
    axes.grid(True, alpha=0.35)
    axes.legend()

    plot_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(plot_path, format=normalized_format, dpi=160)
    plt.close(figure)

    return WaveformPlot(
        raw_path=loaded_waveforms[0].raw_path,
        plot_path=plot_path,
        format=normalized_format,
        title=effective_title,
        signals=tuple(waveform.signal for waveform in loaded_waveforms),
        step=loaded_waveforms[0].step,
        component=effective_component,
        signal_count=len(loaded_waveforms),
        point_count=point_count,
        downsampled=downsampled_any,
        x_unit=loaded_waveforms[0].x_unit,
        y_unit=loaded_waveforms[0].y_unit if len(y_units) == 1 else "mixed",
        warnings=tuple(warnings),
    )


__all__ = ["SERVICE_SPEC", "WaveformPlot", "plot_waveforms"]
