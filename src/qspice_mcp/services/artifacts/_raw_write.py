"""Shared helpers for single-step raw artifact synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
from typing import TYPE_CHECKING, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from qspice_mcp.core.exceptions import BackendUnavailableError, QSpiceError
from qspice_mcp.services._shared.paths import resolve_workspace_path

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from qspice_mcp.services._backends.waveform import LoadedWaveform, LoadedWaveformTrace

    AxisAlignedWaveform = LoadedWaveform | LoadedWaveformTrace

_RAWWRITE_MODULE_CANDIDATES: tuple[str, ...] = ()
_RAW_HEADER_ENCODING = "utf_16_le"
_TRANSIENT_AXIS_NAMES = frozenset({"", "time"})
_FREQUENCY_AXIS_NAMES = frozenset({"frequency"})
_REAL_SCALAR_AXIS_NAMES = _TRANSIENT_AXIS_NAMES | _FREQUENCY_AXIS_NAMES
_FREQUENCY_REAL_PLOT_NAME = "Frequency Response Analysis"

RawTraceValues = NDArray[np.float64] | NDArray[np.complex128]


class _RawWriteInstance(Protocol):
    def add_trace(self, trace: object) -> None: ...

    def save(self, filename: str | Path) -> None: ...


class _RawWriteFactory(Protocol):
    def __call__(
        self,
        plot_name: str | None = None,
        fastacces: bool = True,
        numtype: str = "auto",
        encoding: str = "utf_16_le",
    ) -> _RawWriteInstance: ...


class _TraceFactory(Protocol):
    def __call__(
        self,
        name: str,
        data: NDArray[np.float64],
        whattype: str = "voltage",
        numerical_type: str = "",
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class RawTraceSeries:
    """One named real-valued trace to persist into a derived raw artifact."""

    trace_name: str
    source_signal: str
    values: RawTraceValues


@dataclass(frozen=True, slots=True)
class RawStepBlock:
    """One exported simulation step for stepped raw synthesis."""

    axis_values: NDArray[np.float64]
    traces: tuple[RawTraceSeries, ...]


def load_rawwrite_api() -> tuple[_RawWriteFactory | None, _TraceFactory | None, str | None]:
    """Return the first locally available RawWrite backend."""

    for module_name in _RAWWRITE_MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        raw_write = getattr(module, "RawWrite", None)
        trace = getattr(module, "Trace", None)
        if raw_write is None or trace is None:
            continue
        return cast("_RawWriteFactory", raw_write), cast("_TraceFactory", trace), module_name
    return None, None, None


def _normalized_axis_name(axis_name: str | None) -> str:
    return (axis_name or "").strip().lower()


def default_plot_name(axis_name: str | None) -> str:
    """Return the default plot title for one exported axis kind."""

    if _normalized_axis_name(axis_name) == "frequency":
        return "AC Analysis"
    return "Transient Analysis"


def axis_trace_name(axis_name: str | None) -> str:
    """Return the persisted axis trace name."""

    return axis_name if axis_name else "time"


def axis_trace_type(axis_name: str | None) -> str:
    """Return the RawWrite trace type for one axis."""

    if _normalized_axis_name(axis_name) == "frequency":
        return "frequency"
    return "time"


def signal_trace_type(signal: str) -> str:
    """Infer the RawWrite trace type for one signal name."""

    if signal.strip().lower().startswith("i("):
        return "current"
    return "voltage"


def derived_trace_name(signal: str, *, component: str, complex_source: bool) -> str:
    """Return a stable persisted trace name for one waveform selection."""

    if component == "auto":
        return signal
    if component == "real" and not complex_source:
        return signal
    return f"{component}({signal})"


def _supports_clean_room_writer(axis_name_value: str | None) -> bool:
    """Return whether the clean-room writer can persist this axis kind."""

    return _normalized_axis_name(axis_name_value) in _REAL_SCALAR_AXIS_NAMES


def _requires_complex_writer(traces: Sequence[RawTraceSeries]) -> bool:
    """Return whether any exported trace requires complex-valued persistence."""

    return any(np.iscomplexobj(trace.values) for trace in traces)


def _supports_complex_clean_room_writer(
    axis_name_value: str | None,
    traces: Sequence[RawTraceSeries],
) -> bool:
    """Return whether the clean-room writer can persist this complex slice."""

    return _requires_complex_writer(traces) and (
        _normalized_axis_name(axis_name_value) == "frequency"
    )


def _clean_room_plot_name(
    *,
    plot_name: str,
    axis_name_value: str | None,
    complex_export: bool,
) -> str:
    """Normalize plot titles that would otherwise force complex AC parsing."""

    if _normalized_axis_name(axis_name_value) != "frequency":
        return plot_name
    if complex_export:
        return plot_name
    if plot_name.strip().lower() == "ac analysis":
        return _FREQUENCY_REAL_PLOT_NAME
    return plot_name


def _normalize_axis_values(axis_values: NDArray[np.float64]) -> NDArray[np.float64]:
    """Normalize the exported axis to a one-dimensional float64 array."""

    normalized = np.ravel(np.asarray(axis_values, dtype=np.float64))
    if normalized.size == 0:
        raise ValueError("At least one axis sample is required for raw export.")
    return normalized


def _normalize_trace_values(
    trace: RawTraceSeries,
    *,
    point_count: int,
) -> NDArray[np.float64]:
    """Normalize one exported trace to a one-dimensional real float64 array."""

    if np.iscomplexobj(trace.values):
        raise ValueError(
            f"Derived raw export only supports real-valued traces; {trace.trace_name} was complex."
        )
    normalized = np.ravel(np.asarray(trace.values, dtype=np.float64))
    if normalized.shape[0] != point_count:
        raise ValueError("Derived trace length must match the shared axis length for raw export.")
    return normalized


def _normalize_complex_trace_values(
    trace: RawTraceSeries,
    *,
    point_count: int,
) -> NDArray[np.complex128]:
    """Normalize one exported trace to a one-dimensional complex array."""

    normalized = np.ravel(np.asarray(trace.values))
    if normalized.shape[0] != point_count:
        raise ValueError("Derived trace length must match the shared axis length for raw export.")
    return cast("NDArray[np.complex128]", np.asarray(normalized, dtype=np.complex128))


def _clean_room_header(
    *,
    plot_name: str,
    axis_trace_name_value: str,
    axis_name_value: str | None,
    axis_values: NDArray[np.float64],
    traces: Sequence[RawTraceSeries],
    flags: str,
    offset_value: float,
) -> bytes:
    """Return a minimal UTF-16LE LTspice-style header for real scalar raw export."""

    variable_lines = [
        f"\t0\t{axis_trace_name_value}\t{axis_trace_type(axis_name_value)}",
        *[
            f"\t{index}\t{trace.trace_name}\t{signal_trace_type(trace.source_signal)}"
            for index, trace in enumerate(traces, start=1)
        ],
    ]
    header_text = "\n".join(
        [
            "Title: * qspice_mcp clean-room raw writer",
            f"Date: {datetime.now().ctime()}",
            f"Plotname: {plot_name}",
            f"Flags: {flags}",
            f"No. Variables: {len(traces) + 1}",
            f"No. Points:            {axis_values.shape[0]}",
            f"Offset:   {offset_value:.16e}",
            "Command: Linear Technology Corporation LTspice XVII",
            "Variables:",
            *variable_lines,
            "Binary:",
            "",
        ]
    )
    return header_text.encode(_RAW_HEADER_ENCODING)


def _write_clean_room_real_raw(
    *,
    destination: Path,
    plot_name: str,
    axis_trace_name_value: str,
    axis_name_value: str | None,
    axis_values: NDArray[np.float64],
    traces: Sequence[RawTraceSeries],
) -> None:
    """Write a narrow real-valued shared-axis raw artifact without optional backends."""

    normalized_axis = _normalize_axis_values(axis_values)
    normalized_traces = tuple(
        _normalize_trace_values(trace, point_count=normalized_axis.shape[0]) for trace in traces
    )
    payload = b"".join(
        [
            np.asarray(normalized_axis, dtype="<f8").tobytes(),
            *[
                np.asarray(trace_values, dtype="<f4").tobytes()
                for trace_values in normalized_traces
            ],
        ]
    )
    header = _clean_room_header(
        plot_name=plot_name,
        axis_trace_name_value=axis_trace_name_value,
        axis_name_value=axis_name_value,
        axis_values=normalized_axis,
        traces=traces,
        flags="real fastaccess",
        offset_value=float(normalized_axis[0]),
    )
    destination.write_bytes(header + payload)


def _normalize_step_blocks(
    steps: Sequence[RawStepBlock],
) -> tuple[RawStepBlock, NDArray[np.float64], tuple[RawTraceValues, ...]]:
    """Normalize stepped raw blocks into one flattened axis and trace set."""

    if not steps:
        raise ValueError("At least one step is required for stepped raw export.")

    first_step = steps[0]
    if not first_step.traces:
        raise ValueError("At least one trace is required for stepped raw export.")

    expected_trace_names = tuple(trace.trace_name for trace in first_step.traces)
    complex_export = any(
        np.iscomplexobj(trace.values) for step_block in steps for trace in step_block.traces
    )
    normalized_step_axes: list[NDArray[np.float64]] = []
    normalized_trace_chunks: list[list[RawTraceValues]] = [
        [] for _ in range(len(expected_trace_names))
    ]

    step_origin: float | None = None
    for step_block in steps:
        step_trace_names = tuple(trace.trace_name for trace in step_block.traces)
        if step_trace_names != expected_trace_names:
            raise ValueError(
                "Derived trace names must match across all steps for stepped raw export."
            )

        normalized_axis = _normalize_axis_values(step_block.axis_values)
        if step_origin is None:
            step_origin = float(normalized_axis[0])
        elif not np.isclose(float(normalized_axis[0]), step_origin, rtol=0.0, atol=1e-12):
            raise ValueError(
                "Stepped raw export requires each step axis to begin at the same value."
            )
        else:
            normalized_axis = normalized_axis.copy()
            normalized_axis[0] = step_origin

        normalized_step_axes.append(normalized_axis)
        for index, trace in enumerate(step_block.traces):
            normalized_values: RawTraceValues
            if complex_export:
                normalized_values = _normalize_complex_trace_values(
                    trace,
                    point_count=normalized_axis.shape[0],
                )
            else:
                normalized_values = _normalize_trace_values(
                    trace,
                    point_count=normalized_axis.shape[0],
                )
            normalized_trace_chunks[index].append(normalized_values)

    flattened_axis = np.concatenate(normalized_step_axes)
    flattened_traces = tuple(
        cast("RawTraceValues", np.concatenate(trace_chunks))
        for trace_chunks in normalized_trace_chunks
    )
    return first_step, flattened_axis, flattened_traces


def _write_clean_room_real_stepped_raw(
    *,
    destination: Path,
    plot_name: str,
    axis_trace_name_value: str,
    axis_name_value: str | None,
    steps: Sequence[RawStepBlock],
) -> None:
    """Write a narrow real-valued stepped raw artifact."""

    first_step, flattened_axis, flattened_traces = _normalize_step_blocks(steps)
    payload = b"".join(
        [
            np.asarray(flattened_axis, dtype="<f8").tobytes(),
            *[np.asarray(trace_values, dtype="<f4").tobytes() for trace_values in flattened_traces],
        ]
    )
    header = _clean_room_header(
        plot_name=plot_name,
        axis_trace_name_value=axis_trace_name_value,
        axis_name_value=axis_name_value,
        axis_values=flattened_axis,
        traces=first_step.traces,
        flags="real stepped fastaccess",
        offset_value=float(flattened_axis[0]),
    )
    destination.write_bytes(header + payload)


def _write_clean_room_complex_frequency_stepped_raw(
    *,
    destination: Path,
    plot_name: str,
    axis_trace_name_value: str,
    axis_name_value: str | None,
    steps: Sequence[RawStepBlock],
) -> None:
    """Write a narrow complex-valued stepped frequency-domain raw artifact."""

    first_step, flattened_axis, flattened_traces = _normalize_step_blocks(steps)
    payload = b"".join(
        np.column_stack(
            (
                np.real(point_values),
                np.imag(point_values),
            )
        )
        .astype("<f8", copy=False)
        .tobytes()
        for point_values in (
            np.asarray(
                [complex(flattened_axis[index], 0.0)]
                + [trace_values[index] for trace_values in flattened_traces],
                dtype=np.complex128,
            )
            for index in range(flattened_axis.shape[0])
        )
    )
    header = _clean_room_header(
        plot_name=plot_name,
        axis_trace_name_value=axis_trace_name_value,
        axis_name_value=axis_name_value,
        axis_values=flattened_axis,
        traces=first_step.traces,
        flags="complex stepped",
        offset_value=0.0,
    )
    destination.write_bytes(header + payload)


def _write_clean_room_complex_frequency_raw(
    *,
    destination: Path,
    plot_name: str,
    axis_trace_name_value: str,
    axis_name_value: str | None,
    axis_values: NDArray[np.float64],
    traces: Sequence[RawTraceSeries],
) -> None:
    """Write a narrow complex-valued frequency-domain raw artifact."""

    normalized_axis = _normalize_axis_values(axis_values)
    normalized_traces = tuple(
        _normalize_complex_trace_values(trace, point_count=normalized_axis.shape[0])
        for trace in traces
    )
    # Complex AC raws are read reliably by current backends only in normal-access
    # point-interleaved layout, without the fastaccess flag.
    payload = b"".join(
        np.column_stack(
            (
                np.real(point_values),
                np.imag(point_values),
            )
        )
        .astype("<f8", copy=False)
        .tobytes()
        for point_values in (
            np.asarray(
                [complex(normalized_axis[index], 0.0)]
                + [trace_values[index] for trace_values in normalized_traces],
                dtype=np.complex128,
            )
            for index in range(normalized_axis.shape[0])
        )
    )
    header = _clean_room_header(
        plot_name=plot_name,
        axis_trace_name_value=axis_trace_name_value,
        axis_name_value=axis_name_value,
        axis_values=normalized_axis,
        traces=traces,
        flags="complex",
        offset_value=0.0,
    )
    destination.write_bytes(header + payload)


def ensure_matching_axes(waveforms: Sequence[AxisAlignedWaveform]) -> AxisAlignedWaveform:
    """Validate that selected waveforms can share a single-step merged axis."""

    if not waveforms:
        raise ValueError("At least one waveform is required.")
    anchor = waveforms[0]
    normalized_axis_name = _normalized_axis_name(anchor.axis_name)
    for waveform in waveforms[1:]:
        if waveform.step != anchor.step:
            raise ValueError("Selected waveforms resolved to different simulation steps.")
        if _normalized_axis_name(waveform.axis_name) != normalized_axis_name:
            raise ValueError("Selected waveforms do not share the same axis name.")
        if waveform.x.shape != anchor.x.shape or not np.array_equal(waveform.x, anchor.x):
            raise ValueError("Selected waveforms do not share a common axis after filtering.")
    return anchor


def resolve_raw_output_path(
    source_raw_path: Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None,
    default_suffix: str,
) -> Path:
    """Resolve the destination path for one derived raw artifact."""

    destination = (
        resolve_workspace_path(output_path, workspace_root=workspace_root)
        if output_path is not None
        else (source_raw_path.parent / f"{source_raw_path.stem}{default_suffix}").resolve(
            strict=False
        )
    )
    if destination.suffix == "":
        destination = destination.with_suffix(".qraw")
    return destination.resolve(strict=False)


def write_single_step_raw(
    *,
    destination: Path,
    plot_name: str | None,
    axis_name_value: str | None,
    axis_values: NDArray[np.float64],
    traces: Sequence[RawTraceSeries],
) -> tuple[str, str]:
    """Write one single-step raw artifact from a shared axis and trace set."""

    if not traces:
        raise ValueError("At least one trace is required for raw export.")
    trace_names = tuple(trace.trace_name for trace in traces)
    if len(set(trace_names)) != len(trace_names):
        raise ValueError("Derived trace names must be unique within one raw export.")

    resolved_plot_name = plot_name or default_plot_name(axis_name_value)
    resolved_axis_trace_name = axis_trace_name(axis_name_value)
    destination.parent.mkdir(parents=True, exist_ok=True)

    complex_export = _requires_complex_writer(traces)

    if _supports_clean_room_writer(axis_name_value) or _supports_complex_clean_room_writer(
        axis_name_value,
        traces,
    ):
        clean_room_plot_name = _clean_room_plot_name(
            plot_name=resolved_plot_name,
            axis_name_value=axis_name_value,
            complex_export=complex_export,
        )
        if complex_export:
            _write_clean_room_complex_frequency_raw(
                destination=destination,
                plot_name=clean_room_plot_name,
                axis_trace_name_value=resolved_axis_trace_name,
                axis_name_value=axis_name_value,
                axis_values=axis_values,
                traces=traces,
            )
        else:
            _write_clean_room_real_raw(
                destination=destination,
                plot_name=clean_room_plot_name,
                axis_trace_name_value=resolved_axis_trace_name,
                axis_name_value=axis_name_value,
                axis_values=axis_values,
                traces=traces,
            )
        return clean_room_plot_name, resolved_axis_trace_name

    raw_write_factory, trace_factory, backend_name = load_rawwrite_api()
    if raw_write_factory is None or trace_factory is None or backend_name is None:
        raise BackendUnavailableError(
            "No compatible local RawWrite backend is installed "
            "for non-transient derived raw export. qspice-mcp currently ships a "
            "clean-room writer for real-valued traces on a shared time or "
            "frequency axis, plus complex single-step traces on a shared "
            "frequency axis."
        )

    writer = raw_write_factory(plot_name=resolved_plot_name)
    writer.add_trace(
        trace_factory(
            resolved_axis_trace_name,
            np.asarray(axis_values, dtype=np.float64),
            whattype=axis_trace_type(axis_name_value),
        )
    )
    for trace in traces:
        writer.add_trace(
            trace_factory(
                trace.trace_name,
                np.asarray(trace.values, dtype=np.float64),
                whattype=signal_trace_type(trace.source_signal),
            )
        )
    try:
        writer.save(destination)
    except Exception as exc:
        raise QSpiceError(
            "Failed to write derived raw artifact to "
            f"{destination.name} using {backend_name}.RawWrite."
        ) from exc

    return resolved_plot_name, resolved_axis_trace_name


def write_stepped_raw(
    *,
    destination: Path,
    plot_name: str | None,
    axis_name_value: str | None,
    steps: Sequence[RawStepBlock],
) -> tuple[str, str]:
    """Write one stepped raw artifact from multiple resolved steps."""

    if not steps:
        raise ValueError("At least one step is required for stepped raw export.")
    complex_export = any(
        np.iscomplexobj(trace.values) for step_block in steps for trace in step_block.traces
    )
    if complex_export:
        if not _supports_complex_clean_room_writer(
            axis_name_value,
            tuple(trace for step_block in steps for trace in step_block.traces),
        ):
            raise BackendUnavailableError(
                "qspice-mcp currently ships a stepped clean-room raw writer only for "
                "real-valued traces on a shared time or frequency axis, plus complex-valued "
                "traces on a shared frequency axis."
            )
    elif not _supports_clean_room_writer(axis_name_value):
        raise BackendUnavailableError(
            "qspice-mcp currently ships a stepped clean-room raw writer only for "
            "real-valued traces on a shared time or frequency axis, plus complex-valued "
            "traces on a shared frequency axis."
        )

    resolved_plot_name = plot_name or default_plot_name(axis_name_value)
    resolved_axis_trace_name = axis_trace_name(axis_name_value)
    destination.parent.mkdir(parents=True, exist_ok=True)

    clean_room_plot_name = _clean_room_plot_name(
        plot_name=resolved_plot_name,
        axis_name_value=axis_name_value,
        complex_export=complex_export,
    )
    if complex_export:
        _write_clean_room_complex_frequency_stepped_raw(
            destination=destination,
            plot_name=clean_room_plot_name,
            axis_trace_name_value=resolved_axis_trace_name,
            axis_name_value=axis_name_value,
            steps=steps,
        )
    else:
        _write_clean_room_real_stepped_raw(
            destination=destination,
            plot_name=clean_room_plot_name,
            axis_trace_name_value=resolved_axis_trace_name,
            axis_name_value=axis_name_value,
            steps=steps,
        )
    return clean_room_plot_name, resolved_axis_trace_name


__all__ = [
    "RawStepBlock",
    "RawTraceSeries",
    "axis_trace_name",
    "axis_trace_type",
    "default_plot_name",
    "derived_trace_name",
    "ensure_matching_axes",
    "load_rawwrite_api",
    "resolve_raw_output_path",
    "signal_trace_type",
    "write_single_step_raw",
    "write_stepped_raw",
]
