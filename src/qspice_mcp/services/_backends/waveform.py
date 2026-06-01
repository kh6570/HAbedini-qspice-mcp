"""Shared helpers for RawRead-backed waveform services."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from qspice_mcp.core.budgets import DEFAULT_BUDGET, DataBudget
from qspice_mcp.core.exceptions import BackendUnavailableError, BudgetExceededError, ParseError
from qspice_mcp.services._internals.step_filters import resolve_step_selection
from qspice_mcp.services._shared.paths import validate_existing_file, validate_time_window
from qspice_mcp.services.waveform.read_log import LogStepVariable
from qspice_mcp.services.waveform.read_log import read_log as read_log_service

if TYPE_CHECKING:
    from collections.abc import Mapping

_RAWREAD_MODULE_CANDIDATES: tuple[str, ...] = ()
_MIN_WAVEFORM_POINTS = 2
_CLEAN_ROOM_RAW_TITLE = "Title: * qspice_mcp clean-room raw writer"
_CLEAN_ROOM_BINARY_LABEL = "Binary:".encode("utf_16_le")
_CLEAN_ROOM_VALUES_LABEL = "Values:".encode("utf_16_le")
_TEXT_BINARY_LABEL = b"Binary:"
_TEXT_VALUES_LABEL = b"Values:"
_STEP_AXIS_TOLERANCE = 1e-12
_VARIABLE_HEADER_PART_COUNT = 3
_TEXT_HEADER_ENCODINGS = ("utf-8-sig", "cp1252", "latin1")
_SUPPORTED_EXTERNAL_RAW_FLAGS = frozenset(
    {"real", "complex", "stepped", "fastaccess", "forward", "log", "linear", "double"}
)
_DOUBLE_PRECISION_COMMANDS = ("qspice", "ngspice", "xyce")

WaveformComponent = Literal["auto", "real", "imag", "magnitude", "phase"]
WaveArray = NDArray[np.float64] | NDArray[np.complex128]


class _RawReadProtocol(Protocol):
    def get_trace_names(self) -> list[str] | tuple[str, ...]: ...

    def get_steps(self, **kwargs: object) -> list[int] | range: ...

    def has_axis(self) -> bool: ...

    def get_axis(self, step: int = 0) -> WaveArray | list[float]: ...

    def get_wave(self, trace_ref: str | int, step: int = 0) -> WaveArray: ...

    def get_plot_name(self) -> str | None: ...


class _RawReadFactory(Protocol):
    def __call__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> _RawReadProtocol: ...


@dataclass(frozen=True, slots=True)
class _DecodedRawHeader:
    header_text: str
    header_end: int
    header_format: Literal["utf16le", "text"]
    header_encoding: str
    raw_type: Literal["binary", "values"]


@dataclass(frozen=True, slots=True)
class _CleanRoomRawArtifact:
    plot_name: str | None
    trace_names: tuple[str, ...]
    axis_values: NDArray[np.float64]
    trace_values: tuple[WaveArray, ...]
    step_offsets: tuple[int, ...]


class _CleanRoomRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
        require_repo_title: bool = True,
    ) -> None:
        del dialect, verbose
        artifact = _parse_clean_room_raw(
            Path(raw_filename),
            require_repo_title=require_repo_title,
        )
        selected_traces = _normalize_requested_traces(traces_to_read)
        if selected_traces is not None:
            selected_names = {name.lower() for name in selected_traces}
            filtered = tuple(
                (trace_name, values)
                for trace_name, values in zip(
                    artifact.trace_names[1:], artifact.trace_values, strict=True
                )
                if trace_name.lower() in selected_names
            )
            trace_names = (artifact.trace_names[0], *(name for name, _ in filtered))
            trace_values = tuple(values for _, values in filtered)
        else:
            trace_names = artifact.trace_names
            trace_values = artifact.trace_values
        self._plot_name = artifact.plot_name
        self._trace_names = trace_names
        self._axis_values = artifact.axis_values
        self._trace_values = trace_values
        self._step_offsets = artifact.step_offsets

    def get_trace_names(self) -> tuple[str, ...]:
        return self._trace_names

    def get_steps(self, **kwargs: object) -> range:
        if kwargs:
            raise TypeError(
                "Clean-room raw reader requires sibling .log metadata for step_filters."
            )
        return range(len(self._step_offsets))

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> NDArray[np.float64]:
        start, end = self._step_bounds(step)
        return self._axis_values[start:end]

    def get_wave(self, trace_ref: str | int, step: int = 0) -> WaveArray:
        trace_name = self._trace_names[trace_ref] if isinstance(trace_ref, int) else trace_ref
        if trace_name == self._trace_names[0]:
            return self.get_axis(step=step)

        by_name = {
            name.lower(): values
            for name, values in zip(self._trace_names[1:], self._trace_values, strict=True)
        }
        try:
            full_trace = by_name[trace_name.lower()]
        except KeyError as exc:
            available = ", ".join(self._trace_names[1:])
            raise ValueError(
                f"Signal not found in clean-room raw file: {trace_name}. "
                f"Available signals: {available}"
            ) from exc
        start, end = self._step_bounds(step)
        return full_trace[start:end]

    def get_plot_name(self) -> str | None:
        return self._plot_name

    def _step_bounds(self, step: int) -> tuple[int, int]:
        if step < 0 or step >= len(self._step_offsets):
            raise ValueError(f"Step index {step} is not available in this raw file.")
        start = self._step_offsets[step]
        end = (
            self._step_offsets[step + 1]
            if step + 1 < len(self._step_offsets)
            else int(self._axis_values.shape[0])
        )
        return start, end


def _normalize_requested_traces(
    traces_to_read: None | str | list[str] | tuple[str, ...],
) -> tuple[str, ...] | None:
    if traces_to_read is None:
        return None
    requested: tuple[str, ...]
    if isinstance(traces_to_read, str):
        requested = (traces_to_read,)
    else:
        requested = tuple(str(item) for item in traces_to_read)
    normalized = tuple(item.strip() for item in requested if item.strip())
    return normalized or None


def _parse_header_field(header_text: str, prefix: str) -> str | None:
    for line in header_text.splitlines():
        if line.startswith(prefix):
            value = line.removeprefix(prefix).strip()
            return value or None
    return None


def _parse_step_offsets(axis_values: NDArray[np.float64], *, stepped: bool) -> tuple[int, ...]:
    if not stepped or axis_values.size == 0:
        return (0,)
    origin = float(axis_values[0])
    repeated_origin = np.flatnonzero(
        np.isclose(axis_values, origin, rtol=0.0, atol=_STEP_AXIS_TOLERANCE)
    )
    offsets: list[int] = []
    for index in repeated_origin.tolist():
        if not offsets or index != offsets[-1]:
            offsets.append(int(index))
    if len(offsets) <= 1 and axis_values.size > 1:
        decreasing_offsets = np.flatnonzero(np.diff(axis_values) < -_STEP_AXIS_TOLERANCE) + 1
        for index in decreasing_offsets.tolist():
            if not offsets or index != offsets[-1]:
                offsets.append(int(index))
    if not offsets or offsets[0] != 0:
        offsets.insert(0, 0)
    return tuple(offsets)


def _parse_clean_room_payload(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    complex_data: bool,
) -> tuple[NDArray[np.float64], tuple[WaveArray, ...]]:
    if complex_data:
        expected_scalars = point_count * variable_count * 2
        raw_scalars = np.frombuffer(payload, dtype="<f8", count=expected_scalars)
        if raw_scalars.size != expected_scalars:
            raise ParseError("Clean-room raw payload was shorter than its header declared.")
        complex_matrix = raw_scalars.reshape(point_count, variable_count, 2)
        complex_values = (complex_matrix[:, :, 0] + 1j * complex_matrix[:, :, 1]).astype(
            np.complex128, copy=False
        )
        axis_values = np.asarray(np.real(complex_values[:, 0]), dtype=np.float64)
        trace_values = tuple(
            np.asarray(complex_values[:, index], dtype=np.complex128)
            for index in range(1, variable_count)
        )
        return axis_values, trace_values

    axis_bytes = point_count * np.dtype("<f8").itemsize
    trace_bytes = point_count * np.dtype("<f4").itemsize
    minimum_bytes = axis_bytes + ((variable_count - 1) * trace_bytes)
    if len(payload) < minimum_bytes:
        raise ParseError("Clean-room raw payload was shorter than its header declared.")
    axis_values = np.frombuffer(payload[:axis_bytes], dtype="<f8", count=point_count).astype(
        np.float64,
        copy=False,
    )
    trace_values = tuple(
        np.frombuffer(
            payload[axis_bytes + (index * trace_bytes) : axis_bytes + ((index + 1) * trace_bytes)],
            dtype="<f4",
            count=point_count,
        ).astype(np.float64)
        for index in range(variable_count - 1)
    )
    return axis_values, trace_values


def _parse_fastaccess_payload(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    trace_dtype: str,
    complex_data: bool,
) -> tuple[NDArray[np.float64], tuple[WaveArray, ...]]:
    axis_bytes = point_count * np.dtype("<f8").itemsize
    trace_bytes = point_count * np.dtype(trace_dtype).itemsize
    minimum_bytes = axis_bytes + ((variable_count - 1) * trace_bytes)
    if len(payload) < minimum_bytes:
        raise ParseError("Raw payload was shorter than its header declared.")
    axis_values = np.frombuffer(payload[:axis_bytes], dtype="<f8", count=point_count).astype(
        np.float64,
        copy=False,
    )
    if complex_data:
        trace_values = tuple(
            cast(
                "WaveArray",
                np.frombuffer(
                    payload[
                        axis_bytes + (index * trace_bytes) : axis_bytes
                        + ((index + 1) * trace_bytes)
                    ],
                    dtype=trace_dtype,
                    count=point_count,
                ).astype(np.complex128),
            )
            for index in range(variable_count - 1)
        )
    else:
        trace_values = tuple(
            cast(
                "WaveArray",
                np.frombuffer(
                    payload[
                        axis_bytes + (index * trace_bytes) : axis_bytes
                        + ((index + 1) * trace_bytes)
                    ],
                    dtype=trace_dtype,
                    count=point_count,
                ).astype(np.float64),
            )
            for index in range(variable_count - 1)
        )
    return axis_values, trace_values


def _parse_point_interleaved_payload(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    complex_data: bool,
    real_trace_dtype: str = "<f4",
) -> tuple[NDArray[np.float64], tuple[WaveArray, ...]]:
    trace_count = variable_count - 1
    axis_dtype = np.dtype("<f8")
    if complex_data:
        complex_trace_dtype = np.dtype("<c16")
        minimum_bytes = point_count * (
            axis_dtype.itemsize + (trace_count * complex_trace_dtype.itemsize)
        )
        if len(payload) < minimum_bytes:
            raise ParseError("Raw payload was shorter than its header declared.")
        if trace_count == 0:
            axis_values = np.frombuffer(payload[:minimum_bytes], dtype="<f8", count=point_count)
            return axis_values.astype(np.float64, copy=False), ()
        record_dtype = np.dtype([("axis", "<f8"), ("traces", "<c16", (trace_count,))])
        records = np.frombuffer(payload[:minimum_bytes], dtype=record_dtype, count=point_count)
        axis_values = np.asarray(records["axis"], dtype=np.float64)
        trace_matrix = np.asarray(records["traces"], dtype=np.complex128)
        trace_values = tuple(
            np.asarray(trace_matrix[:, index], dtype=np.complex128) for index in range(trace_count)
        )
        return axis_values, trace_values

    trace_dtype = np.dtype(real_trace_dtype)
    minimum_bytes = point_count * (axis_dtype.itemsize + (trace_count * trace_dtype.itemsize))
    if len(payload) < minimum_bytes:
        raise ParseError("Raw payload was shorter than its header declared.")
    if trace_count == 0:
        axis_values = np.frombuffer(payload[:minimum_bytes], dtype="<f8", count=point_count)
        return axis_values.astype(np.float64, copy=False), ()
    record_dtype = np.dtype([("axis", "<f8"), ("traces", real_trace_dtype, (trace_count,))])
    records = np.frombuffer(payload[:minimum_bytes], dtype=record_dtype, count=point_count)
    axis_values = np.asarray(records["axis"], dtype=np.float64)
    trace_matrix = np.asarray(records["traces"], dtype=np.float64)
    trace_values = tuple(
        np.asarray(trace_matrix[:, index], dtype=np.float64) for index in range(trace_count)
    )
    return axis_values, trace_values


def _parse_ascii_values_payload(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    complex_data: bool,
    encoding: str,
) -> tuple[NDArray[np.float64], tuple[WaveArray, ...]]:
    try:
        payload_text = payload.decode(encoding, errors="ignore")
    except LookupError as exc:
        raise ParseError(f"Unsupported raw text encoding: {encoding}") from exc

    non_empty_lines = [line.strip() for line in payload_text.splitlines() if line.strip()]
    cursor = 0
    axis_values = np.zeros(point_count, dtype=np.float64)
    if complex_data:
        trace_values: list[WaveArray] = [
            np.zeros(point_count, dtype=np.complex128) for _ in range(variable_count - 1)
        ]
    else:
        trace_values = [np.zeros(point_count, dtype=np.float64) for _ in range(variable_count - 1)]

    for point in range(point_count):
        if cursor >= len(non_empty_lines):
            raise ParseError("Raw values payload ended before all points were read.")
        axis_line = non_empty_lines[cursor]
        cursor += 1
        try:
            point_text, axis_text = axis_line.split("\t", 1)
        except ValueError as exc:
            raise ParseError("Raw values payload had an invalid axis entry.") from exc
        if int(point_text) != point:
            raise ParseError("Raw values payload point indexes were not sequential.")
        axis_values[point] = float(axis_text)

        for trace_index in range(variable_count - 1):
            if cursor >= len(non_empty_lines):
                raise ParseError("Raw values payload ended before all traces were read.")
            value_field = non_empty_lines[cursor].split("\t")[-1].strip()
            cursor += 1
            if complex_data:
                real_text, sep, imag_text = value_field.partition(",")
                if not sep:
                    raise ParseError("Complex raw values payload entry was malformed.")
                cast("NDArray[np.complex128]", trace_values[trace_index])[point] = complex(
                    float(real_text),
                    float(imag_text),
                )
            else:
                cast("NDArray[np.float64]", trace_values[trace_index])[point] = float(value_field)

    return axis_values, tuple(trace_values)


def _decode_utf16_raw_header(raw_bytes: bytes) -> _DecodedRawHeader | None:
    marker_candidates = []
    for encoded_label, raw_type in (
        (_CLEAN_ROOM_BINARY_LABEL, "binary"),
        (_CLEAN_ROOM_VALUES_LABEL, "values"),
    ):
        marker_index = raw_bytes.find(encoded_label)
        if marker_index >= 0:
            marker_candidates.append((marker_index, encoded_label, raw_type))
    if not marker_candidates:
        return None

    marker_index, encoded_label, raw_type = min(marker_candidates, key=lambda item: item[0])

    header_end = marker_index + len(encoded_label)
    while header_end + 1 < len(raw_bytes) and raw_bytes[header_end : header_end + 2] in {
        b"\n\x00",
        b"\r\x00",
    }:
        header_end += 2
    try:
        return _DecodedRawHeader(
            header_text=raw_bytes[:header_end].decode("utf_16_le"),
            header_end=header_end,
            header_format="utf16le",
            header_encoding="utf_16_le",
            raw_type=cast('Literal["binary", "values"]', raw_type),
        )
    except UnicodeDecodeError:
        return None


def _decode_text_raw_header(raw_bytes: bytes) -> _DecodedRawHeader | None:
    lower_bytes = raw_bytes.lower()
    marker_candidates = []
    for encoded_label, raw_type in ((_TEXT_BINARY_LABEL, "binary"), (_TEXT_VALUES_LABEL, "values")):
        marker_index = lower_bytes.find(encoded_label.lower())
        if marker_index >= 0:
            marker_candidates.append((marker_index, encoded_label, raw_type))
    if not marker_candidates:
        return None

    marker_index, encoded_label, raw_type = min(marker_candidates, key=lambda item: item[0])

    header_end = marker_index + len(encoded_label)
    while header_end < len(raw_bytes) and raw_bytes[header_end : header_end + 1] in {
        b"\n",
        b"\r",
    }:
        header_end += 1
    header_bytes = raw_bytes[:header_end]
    for encoding in _TEXT_HEADER_ENCODINGS:
        try:
            return _DecodedRawHeader(
                header_text=header_bytes.decode(encoding),
                header_end=header_end,
                header_format="text",
                header_encoding=encoding,
                raw_type=cast('Literal["binary", "values"]', raw_type),
            )
        except UnicodeDecodeError:
            continue
    return _DecodedRawHeader(
        header_text=header_bytes.decode("latin1", errors="replace"),
        header_end=header_end,
        header_format="text",
        header_encoding="latin1",
        raw_type=cast('Literal["binary", "values"]', raw_type),
    )


def _decode_supported_raw_header(raw_bytes: bytes) -> _DecodedRawHeader | None:
    decoded_utf16 = _decode_utf16_raw_header(raw_bytes)
    if decoded_utf16 is not None:
        return decoded_utf16

    decoded_text = _decode_text_raw_header(raw_bytes)
    if decoded_text is not None:
        return decoded_text
    return None


def _infer_external_real_trace_dtype(
    *,
    flag_set: set[str],
    command_text: str | None,
) -> str:
    if "double" in flag_set:
        return "<f8"
    normalized_command = (command_text or "").strip().lower()
    if any(keyword in normalized_command for keyword in _DOUBLE_PRECISION_COMMANDS):
        return "<f8"
    return "<f4"


def _should_use_clean_room_binary_layout(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    complex_data: bool,
    fast_access: bool,
    header_format: Literal["utf16le", "text"],
    declared_clean_room_binary_layout: bool,
) -> bool:
    if declared_clean_room_binary_layout:
        return True
    if header_format != "utf16le" or fast_access or not complex_data:
        return False
    clean_room_complex_bytes = point_count * variable_count * np.dtype("<f8").itemsize * 2
    return len(payload) >= clean_room_complex_bytes


def _parse_supported_raw_payload(
    payload: bytes,
    *,
    variable_count: int,
    point_count: int,
    complex_data: bool,
    fast_access: bool,
    raw_type: Literal["binary", "values"],
    header_format: Literal["utf16le", "text"],
    header_encoding: str,
    flag_set: set[str],
    command_text: str | None,
    declared_clean_room_binary_layout: bool,
) -> tuple[NDArray[np.float64], tuple[WaveArray, ...]]:
    if raw_type == "values":
        return _parse_ascii_values_payload(
            payload,
            variable_count=variable_count,
            point_count=point_count,
            complex_data=complex_data,
            encoding=header_encoding,
        )
    if _should_use_clean_room_binary_layout(
        payload,
        variable_count=variable_count,
        point_count=point_count,
        complex_data=complex_data,
        fast_access=fast_access,
        header_format=header_format,
        declared_clean_room_binary_layout=declared_clean_room_binary_layout,
    ):
        return _parse_clean_room_payload(
            payload,
            variable_count=variable_count,
            point_count=point_count,
            complex_data=complex_data,
        )
    real_trace_dtype = _infer_external_real_trace_dtype(
        flag_set=flag_set,
        command_text=command_text,
    )
    if fast_access:
        return _parse_fastaccess_payload(
            payload,
            variable_count=variable_count,
            point_count=point_count,
            trace_dtype="<c16" if complex_data else real_trace_dtype,
            complex_data=complex_data,
        )
    return _parse_point_interleaved_payload(
        payload,
        variable_count=variable_count,
        point_count=point_count,
        complex_data=complex_data,
        real_trace_dtype=real_trace_dtype,
    )


def _supports_raw_flags(flag_set: set[str]) -> bool:
    if not flag_set or not flag_set.issubset(_SUPPORTED_EXTERNAL_RAW_FLAGS):
        return False
    if "real" in flag_set and "complex" in flag_set:
        return False
    return "real" in flag_set or "complex" in flag_set


def _parse_clean_room_raw(
    raw_path: Path,
    *,
    require_repo_title: bool = True,
) -> _CleanRoomRawArtifact:
    raw_bytes = raw_path.read_bytes()
    decoded_header = _decode_supported_raw_header(raw_bytes)
    if decoded_header is None:
        artifact_kind = (
            "qspice_mcp clean-room raw artifact" if require_repo_title else "supported raw artifact"
        )
        raise ParseError(f"{raw_path.name} is not a {artifact_kind}.")
    header_text = decoded_header.header_text
    header_end = decoded_header.header_end
    if require_repo_title and not header_text.startswith(_CLEAN_ROOM_RAW_TITLE):
        raise ParseError(f"{raw_path.name} is not a qspice_mcp clean-room raw artifact.")

    variable_count_text = _parse_header_field(header_text, "No. Variables:")
    point_count_text = _parse_header_field(header_text, "No. Points:")
    flags_text = _parse_header_field(header_text, "Flags:")
    if variable_count_text is None or point_count_text is None or flags_text is None:
        raise ParseError(f"Clean-room raw header in {raw_path.name} was incomplete.")

    try:
        variable_count = int(variable_count_text)
        point_count = int(point_count_text)
    except ValueError as exc:
        raise ParseError(f"Clean-room raw header in {raw_path.name} had invalid counts.") from exc

    lines = header_text.splitlines()
    try:
        variables_start = lines.index("Variables:") + 1
        section_index = lines.index("Binary:" if decoded_header.raw_type == "binary" else "Values:")
    except ValueError as exc:
        raise ParseError(f"Clean-room raw header in {raw_path.name} was malformed.") from exc

    trace_names: list[str] = []
    for line in lines[variables_start:section_index]:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split("\t")
        if len(parts) < _VARIABLE_HEADER_PART_COUNT:
            raise ParseError(
                f"Clean-room raw header in {raw_path.name} had an invalid variable line."
            )
        trace_names.append(parts[1])
    if len(trace_names) != variable_count:
        raise ParseError(
            f"Clean-room raw header in {raw_path.name} did not match its variable count."
        )

    flag_set = {item.lower() for item in flags_text.split()}
    if not _supports_raw_flags(flag_set):
        raise ParseError(f"Raw header in {raw_path.name} declared unsupported flags.")
    command_text = _parse_header_field(header_text, "Command:")
    uses_clean_room_binary_layout = header_text.startswith(_CLEAN_ROOM_RAW_TITLE)
    axis_values, trace_values = _parse_supported_raw_payload(
        raw_bytes[header_end:],
        variable_count=variable_count,
        point_count=point_count,
        complex_data="complex" in flag_set,
        fast_access="fastaccess" in flag_set,
        raw_type=decoded_header.raw_type,
        header_format=decoded_header.header_format,
        header_encoding=decoded_header.header_encoding,
        flag_set=flag_set,
        command_text=command_text,
        declared_clean_room_binary_layout=uses_clean_room_binary_layout,
    )
    return _CleanRoomRawArtifact(
        plot_name=_parse_header_field(header_text, "Plotname:"),
        trace_names=tuple(trace_names),
        axis_values=axis_values,
        trace_values=trace_values,
        step_offsets=_parse_step_offsets(axis_values, stepped="stepped" in flag_set),
    )


def _try_open_clean_room_reader(
    raw_path: Path,
    *,
    traces_to_read: None | str | list[str] | tuple[str, ...] = None,
) -> _RawReadProtocol | None:
    try:
        raw_bytes = raw_path.read_bytes()
    except OSError:
        return None
    decoded_header = _decode_supported_raw_header(raw_bytes)
    if decoded_header is None:
        return None
    header_text = decoded_header.header_text
    if not header_text.startswith(_CLEAN_ROOM_RAW_TITLE):
        return None
    try:
        return _CleanRoomRawRead(
            raw_path,
            traces_to_read=traces_to_read,
            verbose=False,
            require_repo_title=True,
        )
    except ParseError:
        return None


def _try_open_compatible_supported_reader(
    raw_path: Path,
    *,
    traces_to_read: None | str | list[str] | tuple[str, ...] = None,
) -> _RawReadProtocol | None:
    try:
        decoded_header = _decode_supported_raw_header(raw_path.read_bytes())
    except OSError:
        decoded_header = None
    if decoded_header is None:
        return None
    header_text = decoded_header.header_text
    flags_text = None
    if not header_text.startswith(_CLEAN_ROOM_RAW_TITLE):
        flags_text = _parse_header_field(header_text, "Flags:")
    if flags_text is None:
        return None
    if not _supports_raw_flags({item.lower() for item in flags_text.split()}):
        return None
    try:
        reader = _CleanRoomRawRead(
            raw_path,
            traces_to_read=traces_to_read,
            verbose=False,
            require_repo_title=False,
        )
    except ParseError:
        return None
    return reader


@dataclass(frozen=True, slots=True)
class LoadedWaveform:
    """Normalized waveform data ready for service-level use."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    component: str
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    complex_source: bool
    x_unit: str
    y_unit: str


@dataclass(frozen=True, slots=True)
class LoadedWaveformTrace:
    """Waveform data ready for artifact export, preserving native complex traces."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    component: str
    x: NDArray[np.float64]
    y: WaveArray
    complex_source: bool
    x_unit: str
    y_unit: str


@dataclass(frozen=True, slots=True)
class _ResolvedWaveformPayload:
    """Resolved raw-reader payload before any component projection."""

    raw_path: Path
    plot_name: str | None
    axis_name: str | None
    signal: str
    step: int
    x: NDArray[np.float64]
    y: WaveArray


def _load_rawread_factory() -> tuple[_RawReadFactory | None, str | None]:
    """Return the first locally available RawRead backend."""

    for module_name in _RAWREAD_MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        raw_read = getattr(module, "RawRead", None)
        if raw_read is None:
            continue
        return cast("_RawReadFactory", raw_read), module_name
    return None, None


def build_budget(*, max_points: int | None = None, max_bytes: int | None = None) -> DataBudget:
    """Create a waveform budget from optional overrides."""

    return DataBudget(
        max_points=max_points if max_points is not None else DEFAULT_BUDGET.max_points,
        max_bytes=max_bytes if max_bytes is not None else DEFAULT_BUDGET.max_bytes,
        strategy=DEFAULT_BUDGET.strategy,
    )


def open_raw_reader(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    traces_to_read: None | str | list[str] | tuple[str, ...] = None,
) -> tuple[_RawReadProtocol, Path]:
    """Validate one `.qraw` file and open it through a supported backend."""

    resolved_path = validate_existing_file(
        raw_path, workspace_root=workspace_root, suffixes=(".qraw",)
    )
    clean_room_reader = _try_open_clean_room_reader(
        resolved_path,
        traces_to_read=traces_to_read,
    )
    if clean_room_reader is not None:
        return clean_room_reader, resolved_path
    raw_read_factory, backend_name = _load_rawread_factory()
    if raw_read_factory is None or backend_name is None:
        compatible_reader = _try_open_compatible_supported_reader(
            resolved_path,
            traces_to_read=traces_to_read,
        )
        if compatible_reader is not None:
            return compatible_reader, resolved_path
        raise BackendUnavailableError(
            "No compatible local RawRead backend "
            "QschEditor backend is installed for waveform access."
        )
    try:
        reader = raw_read_factory(str(resolved_path), traces_to_read=traces_to_read, verbose=False)
    except Exception as exc:
        raise ParseError(
            f"Failed to read waveform data from {resolved_path.name} using {backend_name}.RawRead."
        ) from exc
    return reader, resolved_path


def to_axis_array(values: WaveArray | list[float]) -> NDArray[np.float64]:
    """Normalize axis data to a one-dimensional float array."""

    normalized = np.ravel(np.asarray(values))
    if np.iscomplexobj(normalized):
        if not np.allclose(np.imag(normalized), 0.0):
            raise ValueError("Waveform axis must be real-valued.")
        normalized = np.real(normalized)
    return cast("NDArray[np.float64]", np.asarray(normalized, dtype=np.float64))


def to_wave_array(values: WaveArray) -> WaveArray:
    """Normalize waveform data to a one-dimensional numpy array."""

    return cast("WaveArray", np.ravel(np.asarray(values)))


def has_axis(reader: _RawReadProtocol) -> bool:
    """Return whether the raw file declares a dedicated x-axis trace."""

    axis_member = getattr(reader, "has_axis", None)
    if axis_member is None:
        return False
    try:
        return bool(axis_member()) if callable(axis_member) else bool(axis_member)
    except Exception:
        return False


def read_axis_array(reader: _RawReadProtocol, *, step: int) -> NDArray[np.float64]:
    """Read one waveform axis, falling back to the named axis trace when needed."""

    try:
        return to_axis_array(reader.get_axis(step=step))
    except Exception:
        axis_name = get_axis_name(reader)
        if axis_name is None:
            raise
        return to_axis_array(reader.get_wave(axis_name, step=step))


def get_plot_name(reader: _RawReadProtocol) -> str | None:
    """Return the plot name when the backend exposes one."""

    try:
        plot_name = reader.get_plot_name()
    except Exception:
        return None
    return str(plot_name) if plot_name else None


def get_step_indices(reader: _RawReadProtocol) -> tuple[int, ...]:
    """Return available step indices, defaulting to a single step."""

    try:
        steps = tuple(int(step) for step in reader.get_steps())
    except Exception:
        steps = ()
    return steps or (0,)


def _read_step_variables_for_raw(
    raw_path: Path, *, workspace_root: Path
) -> tuple[LogStepVariable, ...]:
    """Return sibling-log step metadata when it is available."""

    log_path = raw_path.with_suffix(".log")
    if not log_path.is_file():
        return ()
    try:
        inspection = read_log_service(
            log_path,
            workspace_root=workspace_root.resolve(strict=False),
            include_measures=False,
            max_lines=0,
        )
    except Exception:
        return ()
    return inspection.step_variables


def normalize_step(reader: _RawReadProtocol, step: int) -> int:
    """Validate one requested step index against the raw file."""

    available_steps = get_step_indices(reader)
    if step not in available_steps:
        rendered_steps = ", ".join(str(value) for value in available_steps)
        raise ValueError(
            f"Step index {step} is not available in this raw file. "
            f"Available steps: {rendered_steps}"
        )
    return step


def resolve_step_request(
    reader: _RawReadProtocol,
    *,
    raw_path: Path,
    workspace_root: Path,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
) -> int:
    """Resolve one waveform step request from an index or step-filter mapping."""

    available_steps = get_step_indices(reader)
    default_step = available_steps[0]
    if not step_filters:
        return normalize_step(reader, default_step if step is None else step)

    step_variables = _read_step_variables_for_raw(raw_path, workspace_root=workspace_root)
    if step_variables:
        resolved_step = resolve_step_selection(
            step_variables,
            len(available_steps),
            step=step,
            step_filters=step_filters,
            default_step=default_step,
        )
        return normalize_step(reader, resolved_step)

    try:
        matched_steps = tuple(int(value) for value in reader.get_steps(**dict(step_filters)))
    except Exception as exc:
        raise ValueError(
            "step_filters require a sibling .log file or backend-provided "
            "step metadata for this raw artifact."
        ) from exc
    if not matched_steps:
        raise ValueError(
            f"No simulation step matched the requested step_filters: {dict(step_filters)}"
        )
    if len(matched_steps) > 1:
        raise ValueError(
            "step_filters resolved to multiple simulation steps; provide an explicit step index."
        )

    resolved_step = matched_steps[0]
    if step is not None and resolved_step != step:
        raise ValueError("step and step_filters resolve to different simulation steps.")
    return normalize_step(reader, resolved_step)


def get_axis_name(reader: _RawReadProtocol) -> str | None:
    """Return the x-axis trace name when present."""

    trace_names = tuple(str(name) for name in reader.get_trace_names())
    if trace_names and has_axis(reader):
        return trace_names[0]
    return None


def get_signal_names(reader: _RawReadProtocol) -> tuple[str, ...]:
    """Return signal names, excluding the dedicated x-axis trace."""

    trace_names = tuple(str(name) for name in reader.get_trace_names())
    if trace_names and has_axis(reader):
        return trace_names[1:]
    return trace_names


def resolve_signal_name(reader: _RawReadProtocol, signal: str) -> str:
    """Resolve one signal name case-insensitively."""

    signals = get_signal_names(reader)
    by_name = {name.lower(): name for name in signals}
    try:
        return by_name[signal.lower()]
    except KeyError as exc:
        available = ", ".join(signals)
        raise ValueError(
            f"Signal not found in raw file: {signal}. Available signals: {available}"
        ) from exc


def infer_axis_unit(axis_name: str | None) -> str:
    """Infer a user-facing unit label for the x-axis."""

    if axis_name is None:
        return "index"
    normalized = axis_name.strip().lower()
    if normalized == "time":
        return "s"
    if normalized == "frequency":
        return "Hz"
    return "arb"


def infer_signal_unit(signal: str, component: str) -> str:
    """Infer a user-facing unit label for one waveform component."""

    if component == "phase":
        return "deg"
    normalized = signal.strip().lower()
    if normalized.startswith("i("):
        return "A"
    if normalized.startswith("v("):
        return "V"
    if normalized.startswith("p("):
        return "W"
    return "arb"


def select_component(
    values: WaveArray, component: WaveformComponent
) -> tuple[str, NDArray[np.float64], bool]:
    """Project one waveform into a JSON-friendly real-valued series."""

    complex_source = bool(np.iscomplexobj(values))
    normalized_component = component.lower()
    if complex_source:
        effective_component = (
            "magnitude" if normalized_component == "auto" else normalized_component
        )
        if effective_component == "real":
            selected = np.real(values)
        elif effective_component == "imag":
            selected = np.imag(values)
        elif effective_component == "magnitude":
            selected = np.abs(values)
        elif effective_component == "phase":
            selected = np.angle(values, deg=True)
        else:
            raise ValueError(f"Unsupported waveform component: {component}")
    else:
        if normalized_component in {"imag", "phase"}:
            raise ValueError(
                f"Waveform component '{component}' requires complex data, "
                "but the selected signal is real-valued."
            )
        effective_component = "real" if normalized_component == "auto" else normalized_component
        if effective_component == "magnitude":
            selected = np.abs(values)
        elif effective_component == "real":
            selected = np.asarray(values, dtype=np.float64)
        else:
            raise ValueError(f"Unsupported waveform component: {component}")
    return (
        effective_component,
        cast("NDArray[np.float64]", np.asarray(selected, dtype=np.float64)),
        complex_source,
    )


def apply_axis_window(
    axis: NDArray[np.float64],
    values: WaveArray,
    *,
    t_start: float | None,
    t_end: float | None,
) -> tuple[NDArray[np.float64], WaveArray]:
    """Apply an inclusive axis window to one waveform series."""

    validate_time_window(t_start, t_end)
    mask = np.ones(axis.shape[0], dtype=np.bool_)
    if t_start is not None:
        mask &= axis >= t_start
    if t_end is not None:
        mask &= axis <= t_end
    filtered_axis = axis[mask]
    filtered_values = values[mask]
    if filtered_axis.size == 0:
        raise ValueError("No waveform samples remain after applying the requested axis window.")
    return filtered_axis, filtered_values


def _resolve_waveform_payload(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
) -> _ResolvedWaveformPayload:
    """Resolve one waveform trace and axis before component projection."""

    reader, resolved_path = open_raw_reader(raw_path, workspace_root=workspace_root)
    normalized_step = resolve_step_request(
        reader,
        raw_path=resolved_path,
        workspace_root=workspace_root,
        step=step,
        step_filters=step_filters,
    )
    resolved_signal = resolve_signal_name(reader, signal)
    raw_wave = to_wave_array(reader.get_wave(resolved_signal, step=normalized_step))
    if has_axis(reader):
        axis_name = get_axis_name(reader)
        axis = read_axis_array(reader, step=normalized_step)
    else:
        axis_name = None
        axis = cast("NDArray[np.float64]", np.arange(raw_wave.shape[0], dtype=np.float64))
    return _ResolvedWaveformPayload(
        raw_path=resolved_path,
        plot_name=get_plot_name(reader),
        axis_name=axis_name,
        signal=resolved_signal,
        step=normalized_step,
        x=axis,
        y=raw_wave,
    )


def apply_budget(
    axis: NDArray[np.float64],
    values: NDArray[np.float64],
    *,
    budget: DataBudget,
) -> tuple[NDArray[np.float64], NDArray[np.float64], bool]:
    """Downsample one waveform pair to fit the configured response budget."""

    dtype_size = int(axis.dtype.itemsize) + int(values.dtype.itemsize)
    if budget.fits(axis.shape[0], dtype_size=dtype_size):
        return axis, values, False

    target_points = budget.target_points(axis.shape[0], dtype_size=dtype_size)
    if target_points < _MIN_WAVEFORM_POINTS and axis.shape[0] >= _MIN_WAVEFORM_POINTS:
        raise BudgetExceededError(
            "Configured waveform budget cannot fit at least two waveform samples."
        )

    indices = np.unique(np.linspace(0, axis.shape[0] - 1, num=target_points, dtype=int))
    if indices.size == 0:
        raise BudgetExceededError("Configured waveform budget cannot fit any waveform samples.")
    return axis[indices], values[indices], True


def load_waveform(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> LoadedWaveform:
    """Load one waveform series with axis-window filtering applied."""

    payload = _resolve_waveform_payload(
        raw_path,
        workspace_root=workspace_root,
        signal=signal,
        step=step,
        step_filters=step_filters,
    )
    effective_component, values, complex_source = select_component(payload.y, component)
    filtered_axis, filtered_values = apply_axis_window(
        payload.x,
        values,
        t_start=t_start,
        t_end=t_end,
    )
    return LoadedWaveform(
        raw_path=payload.raw_path,
        plot_name=payload.plot_name,
        axis_name=payload.axis_name,
        signal=payload.signal,
        step=payload.step,
        component=effective_component,
        x=filtered_axis,
        y=cast("NDArray[np.float64]", filtered_values),
        complex_source=complex_source,
        x_unit=infer_axis_unit(payload.axis_name),
        y_unit=infer_signal_unit(payload.signal, effective_component),
    )


def load_waveform_trace(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> LoadedWaveformTrace:
    """Load one waveform trace, preserving native complex data when `component="auto"`."""

    payload = _resolve_waveform_payload(
        raw_path,
        workspace_root=workspace_root,
        signal=signal,
        step=step,
        step_filters=step_filters,
    )
    complex_source = bool(np.iscomplexobj(payload.y))
    if complex_source and component == "auto":
        effective_component = "auto"
        selected_values = payload.y
    else:
        effective_component, projected_values, complex_source = select_component(
            payload.y,
            component,
        )
        selected_values = cast("WaveArray", projected_values)

    filtered_axis, filtered_values = apply_axis_window(
        payload.x,
        selected_values,
        t_start=t_start,
        t_end=t_end,
    )
    return LoadedWaveformTrace(
        raw_path=payload.raw_path,
        plot_name=payload.plot_name,
        axis_name=payload.axis_name,
        signal=payload.signal,
        step=payload.step,
        component=effective_component,
        x=filtered_axis,
        y=filtered_values,
        complex_source=complex_source,
        x_unit=infer_axis_unit(payload.axis_name),
        y_unit=infer_signal_unit(
            payload.signal,
            "real" if effective_component == "auto" else effective_component,
        ),
    )


__all__ = [
    "LoadedWaveform",
    "LoadedWaveformTrace",
    "WaveformComponent",
    "apply_budget",
    "build_budget",
    "get_axis_name",
    "get_plot_name",
    "get_signal_names",
    "get_step_indices",
    "has_axis",
    "infer_axis_unit",
    "infer_signal_unit",
    "load_waveform",
    "load_waveform_trace",
    "normalize_step",
    "open_raw_reader",
    "read_axis_array",
    "resolve_signal_name",
    "resolve_step_request",
    "select_component",
    "to_axis_array",
    "to_wave_array",
]
