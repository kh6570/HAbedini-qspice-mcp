"""Service for merging multiple waveform selections into one derived raw artifact."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

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
    from collections.abc import Mapping, Sequence

    from qspice_mcp.services._backends.waveform import LoadedWaveformTrace
    from qspice_mcp.services._internals.step_filters import StepFilterValue


@dataclass(frozen=True, slots=True)
class WaveformMergeInput:
    """One waveform selection to merge into a derived raw artifact."""

    raw_path: str | Path
    signal: str
    label: str | None = None
    step: int | None = None
    step_filters: Mapping[str, object] | None = None
    component: WaveformComponent = "auto"
    t_start: float | None = None
    t_end: float | None = None


@dataclass(frozen=True, slots=True)
class MergedWaveformExport:
    """Metadata for one merged waveform artifact."""

    source_raw_paths: tuple[Path, ...]
    output_path: Path
    plot_name: str
    axis_name: str | None
    axis_trace_name: str
    step: int | None
    point_count: int
    input_count: int
    signal_names: tuple[str, ...]
    trace_names: tuple[str, ...]
    components: tuple[str, ...]
    step_count: int = 1
    resolved_steps: tuple[int, ...] = ()
    output_log_path: Path | None = None
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="merge_waveforms",
    title="Merge Waveforms",
    summary=(
        "Merge multiple filtered waveform selections into one derived raw artifact, "
        "with optional stepped reconstruction."
    ),
    phase="implemented",
    read_only=False,
)


def _normalize_input(
    item: WaveformMergeInput | Mapping[str, object],
) -> WaveformMergeInput:
    if isinstance(item, WaveformMergeInput):
        normalized = item
    else:
        raw_path = item.get("raw_path")
        signal = item.get("signal")
        if not isinstance(raw_path, (str, Path)):
            raise TypeError("Each merge input requires a string or Path raw_path.")
        if not isinstance(signal, str) or not signal.strip():
            raise ValueError("Each merge input requires a non-empty signal.")
        label = item.get("label")
        if label is not None and not isinstance(label, str):
            raise ValueError("Merge input label must be a string when provided.")
        step = item.get("step")
        if step is not None and not isinstance(step, int):
            raise ValueError("Merge input step must be an integer when provided.")
        step_filters = item.get("step_filters")
        if step_filters is not None and not isinstance(step_filters, dict):
            raise ValueError("Merge input step_filters must be a mapping when provided.")
        component = item.get("component", "auto")
        if not isinstance(component, str):
            raise TypeError("Merge input component must be a string when provided.")
        t_start = item.get("t_start")
        if t_start is not None and not isinstance(t_start, (int, float)):
            raise ValueError("Merge input t_start must be numeric when provided.")
        t_end = item.get("t_end")
        if t_end is not None and not isinstance(t_end, (int, float)):
            raise ValueError("Merge input t_end must be numeric when provided.")
        normalized = WaveformMergeInput(
            raw_path=raw_path,
            signal=signal.strip(),
            label=None if label is None else label.strip(),
            step=step,
            step_filters=cast("Mapping[str, object] | None", step_filters),
            component=cast("WaveformComponent", component),
            t_start=None if t_start is None else float(t_start),
            t_end=None if t_end is None else float(t_end),
        )
    if not normalized.signal.strip():
        raise ValueError("Merge input signal cannot be blank.")
    return normalized


def _build_trace_names(
    normalized_inputs: Sequence[WaveformMergeInput],
    waveforms: Sequence[LoadedWaveformTrace],
) -> tuple[str, ...]:
    return tuple(
        cast("str", normalized.label)
        if normalized.label not in {None, ""}
        else (
            waveform.raw_path.stem
            + ":"
            + derived_trace_name(
                waveform.signal,
                component=waveform.component,
                complex_source=waveform.complex_source,
            )
        )
        for normalized, waveform in zip(normalized_inputs, waveforms, strict=True)
    )


def _format_step_value(value: StepFilterValue) -> str:
    if isinstance(value, float):
        return format(value, ".16g")
    return str(value)


def _render_step_log_lines(
    step_values: tuple[dict[str, StepFilterValue], ...],
) -> str:
    total_steps = len(step_values)
    lines = []
    for position, values in enumerate(step_values, start=1):
        rendered_values = values or {"run": position}
        assignments = " ".join(
            f"{name}={_format_step_value(value)}" for name, value in rendered_values.items()
        )
        lines.append(f" {position} of {total_steps} steps: .step {assignments}")
    return "\n".join(lines) + "\n"


def _resolve_step_inputs(
    normalized_inputs: Sequence[WaveformMergeInput],
    *,
    workspace: Path,
) -> tuple[tuple[WaveformMergeInput, ...], tuple[int, ...]]:
    available_steps: tuple[int, ...] | None = None
    resolved_inputs: list[WaveformMergeInput] = []
    for item in normalized_inputs:
        reader, resolved_raw_path = open_raw_reader(item.raw_path, workspace_root=workspace)
        step_indices = get_step_indices(reader)
        if available_steps is None:
            available_steps = step_indices
        elif step_indices != available_steps:
            raise ValueError(
                "All merge inputs must expose the same step indices when all_steps=true."
            )
        resolved_inputs.append(replace(item, raw_path=resolved_raw_path))
    if available_steps is None:
        raise ValueError("inputs must contain at least one waveform selection.")
    return tuple(resolved_inputs), available_steps


def _resolve_step_values(
    source_raw_paths: Sequence[Path],
    *,
    workspace: Path,
    step_count: int,
) -> tuple[tuple[dict[str, StepFilterValue], ...], tuple[str, ...]]:
    blank_values: tuple[dict[str, StepFilterValue], ...] = tuple({} for _ in range(step_count))
    catalogs: list[tuple[dict[str, StepFilterValue], ...]] = []
    for source_raw_path in source_raw_paths:
        catalog = list_steps_service(source_raw_path, workspace_root=workspace)
        values = tuple(summary.values for summary in catalog.steps)
        catalogs.append(values if len(values) == step_count else blank_values)

    chosen_values = next((values for values in catalogs if any(values)), blank_values)
    warnings: list[str] = []
    if any(values != chosen_values for values in catalogs if any(values)):
        warnings.append(
            "Merge inputs reported different step metadata; the first populated step catalog "
            "was used."
        )
    if any(not values for values in chosen_values):
        warnings.append(
            "Source step metadata was incomplete; the merged step log used synthetic run "
            "numbers where needed."
        )
    return chosen_values, tuple(warnings)


def _merge_single_step_waveforms(
    normalized_inputs: Sequence[WaveformMergeInput],
    *,
    workspace: Path,
    output_path: str | Path | None = None,
) -> MergedWaveformExport:
    waveforms = tuple(
        load_waveform_trace(
            item.raw_path,
            workspace_root=workspace,
            signal=item.signal,
            step=item.step,
            step_filters=item.step_filters,
            component=item.component,
            t_start=item.t_start,
            t_end=item.t_end,
        )
        for item in normalized_inputs
    )
    anchor = ensure_matching_axes(waveforms)

    destination = resolve_raw_output_path(
        anchor.raw_path,
        workspace_root=workspace,
        output_path=output_path,
        default_suffix="-merged.qraw",
    )
    source_raw_paths = tuple(waveform.raw_path for waveform in waveforms)
    if destination in source_raw_paths:
        raise ValueError("output_path must differ from all input raw paths for waveform merge.")

    trace_names = _build_trace_names(normalized_inputs, waveforms)
    warnings: list[str] = []
    distinct_plot_names = {
        waveform.plot_name for waveform in waveforms if waveform.plot_name not in {None, ""}
    }
    if len(distinct_plot_names) > 1:
        warnings.append(
            "Merged waveform inputs reported different plot names; the first "
            "input's plot name was used."
        )
    if anchor.axis_name is None:
        warnings.append(
            "Merged source raws did not expose a dedicated axis trace; exported raw uses a "
            "synthetic time axis based on sample index."
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

    return MergedWaveformExport(
        source_raw_paths=source_raw_paths,
        output_path=destination,
        plot_name=plot_name,
        axis_name=anchor.axis_name,
        axis_trace_name=axis_trace_name,
        step=anchor.step,
        point_count=int(anchor.x.shape[0]),
        input_count=len(normalized_inputs),
        signal_names=tuple(waveform.signal for waveform in waveforms),
        trace_names=trace_names,
        components=tuple(waveform.component for waveform in waveforms),
        step_count=1,
        resolved_steps=(anchor.step,),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _merge_all_steps_waveforms(
    normalized_inputs: Sequence[WaveformMergeInput],
    *,
    workspace: Path,
    output_path: str | Path | None = None,
) -> MergedWaveformExport:
    if any(item.step is not None or item.step_filters is not None for item in normalized_inputs):
        raise ValueError("all_steps cannot be combined with per-input step or step_filters.")

    resolved_inputs, available_steps = _resolve_step_inputs(normalized_inputs, workspace=workspace)
    if len(available_steps) <= 1:
        return _merge_single_step_waveforms(
            resolved_inputs,
            workspace=workspace,
            output_path=output_path,
        )

    waveforms_by_step = tuple(
        tuple(
            load_waveform_trace(
                item.raw_path,
                workspace_root=workspace,
                signal=item.signal,
                step=step_index,
                component=item.component,
                t_start=item.t_start,
                t_end=item.t_end,
            )
            for item in resolved_inputs
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
        raise ValueError("Selected waveforms do not share the same axis name across merged steps.")

    source_raw_paths = tuple(Path(item.raw_path).resolve(strict=False) for item in resolved_inputs)
    destination = resolve_raw_output_path(
        source_raw_paths[0],
        workspace_root=workspace,
        output_path=output_path,
        default_suffix="-merged.qraw",
    )
    if destination in source_raw_paths:
        raise ValueError("output_path must differ from all input raw paths for waveform merge.")

    trace_names = _build_trace_names(resolved_inputs, waveforms_by_step[0])
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

    step_values, step_warnings = _resolve_step_values(
        source_raw_paths,
        workspace=workspace,
        step_count=len(available_steps),
    )
    output_log_path = destination.with_suffix(".log").resolve(strict=False)
    output_log_path.write_text(_render_step_log_lines(step_values), encoding="utf-8")

    warnings: list[str] = list(step_warnings)
    distinct_plot_names = {
        waveform.plot_name
        for step_waveforms in waveforms_by_step
        for waveform in step_waveforms
        if waveform.plot_name not in {None, ""}
    }
    if len(distinct_plot_names) > 1:
        warnings.append(
            "Merged waveform inputs reported different plot names; the first "
            "input's plot name was used."
        )
    if anchor.axis_name is None:
        warnings.append(
            "Merged source raws did not expose a dedicated axis trace; exported raw uses a "
            "synthetic time axis based on sample index per step."
        )

    return MergedWaveformExport(
        source_raw_paths=source_raw_paths,
        output_path=destination,
        plot_name=plot_name,
        axis_name=anchor.axis_name,
        axis_trace_name=axis_trace_name,
        step=None,
        point_count=int(sum(step_anchor.x.shape[0] for step_anchor in anchors)),
        input_count=len(resolved_inputs),
        signal_names=tuple(waveform.signal for waveform in waveforms_by_step[0]),
        trace_names=trace_names,
        components=tuple(waveform.component for waveform in waveforms_by_step[0]),
        step_count=len(available_steps),
        resolved_steps=available_steps,
        output_log_path=output_log_path,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def merge_waveforms(
    inputs: Sequence[WaveformMergeInput | Mapping[str, object]],
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    all_steps: bool = False,
) -> MergedWaveformExport:
    """Merge multiple filtered waveform selections into one derived `.qraw` artifact."""

    if not inputs:
        raise ValueError("inputs must contain at least one waveform selection.")

    workspace = workspace_root.resolve(strict=False)
    normalized_inputs = tuple(_normalize_input(item) for item in inputs)
    if all_steps:
        return _merge_all_steps_waveforms(
            normalized_inputs,
            workspace=workspace,
            output_path=output_path,
        )
    return _merge_single_step_waveforms(
        normalized_inputs,
        workspace=workspace,
        output_path=output_path,
    )


__all__ = ["SERVICE_SPEC", "MergedWaveformExport", "WaveformMergeInput", "merge_waveforms"]
