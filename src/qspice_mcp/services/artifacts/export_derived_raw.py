"""Service for exporting selected waveform traces as a derived raw artifact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.waveform import (
    WaveformComponent,
    get_step_indices,
    load_waveform_trace,
    open_raw_reader,
)
from qspice_mcp.services.artifacts._raw_write import (
    RawStepBlock,
    RawTraceSeries,
    derived_trace_name,
    ensure_matching_axes,
    resolve_raw_output_path,
    write_single_step_raw,
    write_stepped_raw,
)
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.list_steps import list_steps as list_steps_service

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from qspice_mcp.services._internals.step_filters import StepFilterValue


@dataclass(frozen=True, slots=True)
class DerivedRawExport:
    """Metadata for one exported derived raw artifact."""

    raw_path: Path
    output_path: Path
    plot_name: str
    axis_name: str | None
    axis_trace_name: str
    step: int | None
    step_count: int
    point_count: int
    resolved_steps: tuple[int, ...]
    signal_names: tuple[str, ...]
    trace_names: tuple[str, ...]
    components: tuple[str, ...]
    output_log_path: Path | None = None
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="export_derived_raw",
    title="Export Derived Raw",
    summary="Write one filtered single-step waveform selection to a derived binary raw artifact.",
    phase="implemented",
    read_only=False,
)


def _export_single_step_raw(
    raw_path: str | Path,
    *,
    workspace: Path,
    requested_signals: tuple[str, ...],
    output_path: str | Path | None = None,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> DerivedRawExport:
    """Write one derived `.qraw` file from selected filtered waveform traces."""
    waveforms = tuple(
        load_waveform_trace(
            raw_path,
            workspace_root=workspace,
            signal=signal,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        for signal in requested_signals
    )
    anchor = ensure_matching_axes(waveforms)

    destination = resolve_raw_output_path(
        anchor.raw_path,
        workspace_root=workspace,
        output_path=output_path,
        default_suffix="-derived.qraw",
    )
    if destination == anchor.raw_path:
        raise ValueError("output_path must differ from raw_path for derived raw export.")

    trace_names = tuple(
        derived_trace_name(
            waveform.signal,
            component=waveform.component,
            complex_source=waveform.complex_source,
        )
        for waveform in waveforms
    )
    plot_name, axis_trace_name = write_single_step_raw(
        destination=destination,
        plot_name=anchor.plot_name,
        axis_name_value=anchor.axis_name,
        axis_values=anchor.x,
        traces=tuple(
            RawTraceSeries(
                trace_name=trace_name,
                source_signal=waveform.signal,
                values=waveform.y,
            )
            for waveform, trace_name in zip(waveforms, trace_names, strict=True)
        ),
    )

    warnings: list[str] = []
    if anchor.axis_name is None:
        warnings.append(
            "Source raw did not expose a dedicated axis trace; exported raw uses a synthetic "
            "time axis based on sample index."
        )

    return DerivedRawExport(
        raw_path=anchor.raw_path,
        output_path=destination.resolve(strict=False),
        plot_name=plot_name,
        axis_name=anchor.axis_name,
        axis_trace_name=axis_trace_name,
        step=anchor.step,
        step_count=1,
        point_count=int(anchor.x.shape[0]),
        resolved_steps=(anchor.step,),
        signal_names=tuple(waveform.signal for waveform in waveforms),
        trace_names=trace_names,
        components=tuple(waveform.component for waveform in waveforms),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _export_all_steps_raw(
    raw_path: str | Path,
    *,
    workspace: Path,
    requested_signals: tuple[str, ...],
    output_path: str | Path | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> DerivedRawExport:
    """Write one stepped derived `.qraw` file from all resolved source steps."""

    reader, resolved_raw_path = open_raw_reader(raw_path, workspace_root=workspace)
    available_steps = get_step_indices(reader)
    if len(available_steps) <= 1:
        return _export_single_step_raw(
            resolved_raw_path,
            workspace=workspace,
            requested_signals=requested_signals,
            output_path=output_path,
            step=available_steps[0],
            component=component,
            t_start=t_start,
            t_end=t_end,
        )

    waveforms_by_step = tuple(
        tuple(
            load_waveform_trace(
                resolved_raw_path,
                workspace_root=workspace,
                signal=signal,
                step=step_index,
                component=component,
                t_start=t_start,
                t_end=t_end,
            )
            for signal in requested_signals
        )
        for step_index in available_steps
    )
    anchors = tuple(ensure_matching_axes(step_waveforms) for step_waveforms in waveforms_by_step)
    anchor = anchors[0]
    normalized_axis_name = (anchor.axis_name or "").strip().lower()
    if any(
        (candidate.axis_name or "").strip().lower() != normalized_axis_name
        for candidate in anchors[1:]
    ):
        raise ValueError(
            "Selected waveforms do not share the same axis name across exported steps."
        )

    destination = resolve_raw_output_path(
        resolved_raw_path,
        workspace_root=workspace,
        output_path=output_path,
        default_suffix="-derived.qraw",
    )
    if destination == resolved_raw_path:
        raise ValueError("output_path must differ from raw_path for derived raw export.")

    trace_names = tuple(
        derived_trace_name(
            waveform.signal,
            component=waveform.component,
            complex_source=waveform.complex_source,
        )
        for waveform in waveforms_by_step[0]
    )
    plot_name, axis_trace_name = write_stepped_raw(
        destination=destination,
        plot_name=anchor.plot_name,
        axis_name_value=anchor.axis_name,
        steps=tuple(
            RawStepBlock(
                axis_values=step_anchor.x,
                traces=tuple(
                    RawTraceSeries(
                        trace_name=trace_name,
                        source_signal=waveform.signal,
                        values=waveform.y,
                    )
                    for waveform, trace_name in zip(step_waveforms, trace_names, strict=True)
                ),
            )
            for step_anchor, step_waveforms in zip(anchors, waveforms_by_step, strict=True)
        ),
    )

    source_step_catalog = list_steps_service(resolved_raw_path, workspace_root=workspace)
    step_values = tuple(summary.values for summary in source_step_catalog.steps)
    if len(step_values) != len(available_steps):
        step_values = tuple({} for _ in available_steps)
    output_log_path = destination.with_suffix(".log").resolve(strict=False)
    output_log_path.write_text(_render_step_log_lines(step_values), encoding="utf-8")

    warnings: list[str] = []
    distinct_plot_names = {
        waveform.plot_name
        for step_waveforms in waveforms_by_step
        for waveform in step_waveforms
        if waveform.plot_name not in {None, ""}
    }
    if len(distinct_plot_names) > 1:
        warnings.append(
            "Source step waveforms reported different plot names; the first step's plot name "
            "was used."
        )
    if anchor.axis_name is None:
        warnings.append(
            "Source raw did not expose a dedicated axis trace; exported raw uses a synthetic "
            "time axis based on sample index per step."
        )
    if any(not values for values in step_values):
        warnings.append(
            "Source step metadata was incomplete; the derived step log used synthetic run "
            "numbers where needed."
        )

    return DerivedRawExport(
        raw_path=resolved_raw_path,
        output_path=destination.resolve(strict=False),
        plot_name=plot_name,
        axis_name=anchor.axis_name,
        axis_trace_name=axis_trace_name,
        step=None,
        step_count=len(available_steps),
        point_count=int(sum(step_anchor.x.shape[0] for step_anchor in anchors)),
        resolved_steps=available_steps,
        signal_names=tuple(waveform.signal for waveform in waveforms_by_step[0]),
        trace_names=trace_names,
        components=tuple(waveform.component for waveform in waveforms_by_step[0]),
        output_log_path=output_log_path,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def export_derived_raw(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signals: tuple[str, ...] | list[str],
    output_path: str | Path | None = None,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    all_steps: bool = False,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> DerivedRawExport:
    """Write one derived `.qraw` file from selected filtered waveform traces."""

    requested_signals = tuple(signal.strip() for signal in signals)
    if not requested_signals:
        raise ValueError("signals must contain at least one entry.")
    if any(not signal for signal in requested_signals):
        raise ValueError("signals cannot contain blank entries.")
    if all_steps and (step is not None or step_filters is not None):
        raise ValueError("all_steps cannot be combined with step or step_filters.")

    workspace = workspace_root.resolve(strict=False)
    if all_steps:
        return _export_all_steps_raw(
            raw_path,
            workspace=workspace,
            requested_signals=requested_signals,
            output_path=output_path,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
    return _export_single_step_raw(
        raw_path,
        workspace=workspace,
        requested_signals=requested_signals,
        output_path=output_path,
        step=step,
        step_filters=step_filters,
        component=component,
        t_start=t_start,
        t_end=t_end,
    )


def _format_step_value(value: StepFilterValue) -> str:
    """Render one step value back into a compact log token."""

    if isinstance(value, float):
        return format(value, ".16g")
    return str(value)


def _render_step_log_lines(
    step_values: tuple[dict[str, StepFilterValue], ...],
) -> str:
    """Render minimal `.step` log lines that `list_steps` can parse again."""

    total_steps = len(step_values)
    lines = []
    for position, values in enumerate(step_values, start=1):
        rendered_values = values or {"run": position}
        assignments = " ".join(
            f"{name}={_format_step_value(value)}" for name, value in rendered_values.items()
        )
        lines.append(f" {position} of {total_steps} steps: .step {assignments}")
    return "\n".join(lines) + "\n"


__all__ = ["SERVICE_SPEC", "DerivedRawExport", "export_derived_raw"]
