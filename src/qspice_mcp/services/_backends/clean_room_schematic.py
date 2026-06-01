"""Minimal clean-room writers for fixed-format QSpice schematic artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ArtifactMissingError, QSpiceError
from qspice_mcp.services.simulation._clean_room_netlist import (
    _build_net_names,
    _decode_qsch_text,
    _extract_quoted_text,
    _normalize_line,
    _parse_qsch_schematic,
)

from .schematic_editor_backend import (
    _GROUND_NET_NAME,
    _normalize_net_name,
    _quote_qsch_string,
    normalize_component_parameters,
)

if TYPE_CHECKING:
    from pathlib import Path

_QSCH_FILE_PREFIX = b"\xff\xd8\xff\xdb"
_QSCH_OPEN = b"\xab"
_QSCH_CLOSE = b"\xbb"
_QSCH_NEWLINE = b"\r\n"
_DIRECTIVE_UTF8_BOM = b"\xef\xbb\xbf"
_TOP_LEVEL_DIRECTIVE_MAX_INDENT = 2
_DIRECTIVE_DEFAULT_X = 400
_DIRECTIVE_DEFAULT_Y = -40
_DIRECTIVE_Y_STEP = 80


@dataclass(frozen=True, slots=True)
class CleanRoomComponentInspection:
    """Repo-owned component metadata parsed from the supported clean-room qsch subset."""

    reference: str
    kind: str
    symbol: str
    value: str | None
    description: str | None
    nodes: tuple[str, ...]
    parameters: dict[str, str]
    raw_parameter_lines: tuple[str, ...]
    position_x: int
    position_y: int
    rotation_degrees: int
    has_subcircuit: bool


@dataclass(frozen=True, slots=True)
class _DirectiveLine:
    raw_line_index: int
    instruction: str


def _tag_open(indent: int, payload: bytes) -> bytes:
    return (b" " * indent) + _QSCH_OPEN + payload + _QSCH_NEWLINE


def _tag_inline(indent: int, payload: bytes) -> bytes:
    return (b" " * indent) + _QSCH_OPEN + payload + _QSCH_CLOSE + _QSCH_NEWLINE


def _tag_text(indent: int, payload: bytes, value: str, *, field_name: str) -> bytes:
    return (
        (b" " * indent)
        + _QSCH_OPEN
        + payload
        + _quoted_utf8_bytes(value, field_name=field_name)
        + _QSCH_CLOSE
        + _QSCH_NEWLINE
    )


def _tag_close(indent: int) -> bytes:
    return (b" " * indent) + _QSCH_CLOSE + _QSCH_NEWLINE


def _quoted_utf8_bytes(value: str, *, field_name: str) -> bytes:
    normalized = str(value)
    if not normalized.strip():
        raise ValueError(f"{field_name} must not be empty.")
    _quote_qsch_string(normalized)
    if "\r" in normalized or "\n" in normalized:
        raise ValueError(f"{field_name} must not contain line breaks.")
    return b'"' + normalized.encode("utf-8") + b'"'


def _component_reference(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    _quote_qsch_string(normalized)
    return normalized


def _rotation_degrees(rotation_code: int) -> int:
    if rotation_code % 2 != 0:
        raise ValueError(
            f"Unsupported qsch component rotation code {rotation_code}; expected quarter turns."
        )
    return int((rotation_code // 2) % 4) * 90


def _coerce_component_parameters(
    attribute_tokens: tuple[str, ...],
) -> tuple[dict[str, str], tuple[str, ...]]:
    raw_parameters: dict[object, object] = {}
    raw_index = 0
    for token in attribute_tokens:
        key, separator, value = token.partition("=")
        if separator and key.strip():
            raw_parameters[key.strip()] = value.strip()
            continue
        raw_parameters[raw_index] = token
        raw_index += 1
    return normalize_component_parameters(raw_parameters)


def _normalize_instruction_text(value: str, *, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    _quote_qsch_string(normalized)
    if "\r" in normalized or "\n" in normalized:
        raise ValueError(f"{field_name} must not contain line breaks.")
    return normalized


def _directive_line_bytes(instruction: str, *, directive_index: int) -> bytes:
    position_y = _DIRECTIVE_DEFAULT_Y - (directive_index * _DIRECTIVE_Y_STEP)
    return (
        (b" " * 2)
        + _QSCH_OPEN
        + f"text ({_DIRECTIVE_DEFAULT_X},{position_y}) 1 0 0 0x1000000 -1 -1 ".encode("ascii")
        + b'"'
        + _DIRECTIVE_UTF8_BOM
        + instruction.encode("utf-8")
        + b'"'
        + _QSCH_CLOSE
        + _QSCH_NEWLINE
    )


def _split_qsch_lines(raw_bytes: bytes) -> tuple[list[bytes], tuple[str, ...]]:
    raw_lines = raw_bytes.splitlines(keepends=True)
    decoded_lines = tuple(_decode_qsch_text(raw_bytes).splitlines())
    if len(raw_lines) != len(decoded_lines):
        raise QSpiceError("Clean-room directive fallback could not align qsch text lines.")
    return raw_lines, decoded_lines


def _normalize_directive_value(value: str) -> str:
    return value.removeprefix("\ufeff").strip()


def _scan_top_level_directives(raw_bytes: bytes) -> tuple[list[bytes], tuple[_DirectiveLine, ...]]:
    raw_lines, decoded_lines = _split_qsch_lines(raw_bytes)
    directives: list[_DirectiveLine] = []
    for raw_line_index, decoded_line in enumerate(decoded_lines):
        indent, normalized_line = _normalize_line(decoded_line)
        if indent > _TOP_LEVEL_DIRECTIVE_MAX_INDENT or not normalized_line.startswith("text "):
            continue
        value = _extract_quoted_text(normalized_line)
        if value is None:
            continue
        instruction = _normalize_directive_value(value)
        if not instruction.startswith("."):
            continue
        directives.append(_DirectiveLine(raw_line_index=raw_line_index, instruction=instruction))
    return raw_lines, tuple(directives)


def _find_root_close_line_index(raw_lines: list[bytes]) -> int | None:
    for index in range(len(raw_lines) - 1, -1, -1):
        normalized = raw_lines[index].rstrip(b"\r\n")
        if normalized == _QSCH_CLOSE:
            return index
    return None


def _blank_schematic_with_instruction_bytes(instruction: str) -> bytes:
    return _QSCH_FILE_PREFIX + b"".join(
        [
            _tag_open(0, b"schematic"),
            _directive_line_bytes(instruction, directive_index=0),
            _tag_close(0),
            _QSCH_NEWLINE,
        ]
    )


def add_instruction_to_supported_schematic(
    schematic_path: Path,
    destination: Path,
    *,
    instruction: str,
) -> None:
    normalized_instruction = _normalize_instruction_text(instruction, field_name="instruction")
    raw_bytes = schematic_path.read_bytes()
    if raw_bytes == blank_schematic_bytes():
        _write_artifact(
            destination,
            _blank_schematic_with_instruction_bytes(normalized_instruction),
        )
        return

    raw_lines, directives = _scan_top_level_directives(raw_bytes)
    root_close_index = _find_root_close_line_index(raw_lines)
    if root_close_index is None:
        raise QSpiceError("Clean-room directive fallback requires a supported qsch root wrapper.")
    raw_lines.insert(
        root_close_index,
        _directive_line_bytes(normalized_instruction, directive_index=len(directives)),
    )
    _write_artifact(destination, _QSCH_FILE_PREFIX + b"".join(raw_lines)[len(_QSCH_FILE_PREFIX) :])


def remove_instruction_from_supported_schematic(
    schematic_path: Path,
    destination: Path,
    *,
    instruction: str,
    regex: bool = False,
) -> bool:
    raw_bytes = schematic_path.read_bytes()
    raw_lines, directives = _scan_top_level_directives(raw_bytes)
    if regex:
        pattern = re.compile(instruction)
        matched_line = next(
            (item for item in directives if pattern.search(item.instruction) is not None),
            None,
        )
    else:
        normalized_instruction = _normalize_instruction_text(instruction, field_name="instruction")
        matched_line = next(
            (item for item in directives if item.instruction == normalized_instruction),
            None,
        )
    if matched_line is None:
        return False
    del raw_lines[matched_line.raw_line_index]
    _write_artifact(destination, _QSCH_FILE_PREFIX + b"".join(raw_lines)[len(_QSCH_FILE_PREFIX) :])
    return True


def inspect_supported_schematic_components(
    schematic_path: Path,
) -> tuple[CleanRoomComponentInspection, ...]:
    components, wires, nets, _ = _parse_qsch_schematic(schematic_path, allow_empty=True)
    if not components:
        return ()

    net_names = _build_net_names(components, wires, nets)
    inspections: list[CleanRoomComponentInspection] = []
    for component in components:
        if component.reference is None:
            continue
        parameters, raw_parameter_lines = _coerce_component_parameters(component.attributes)
        inspections.append(
            CleanRoomComponentInspection(
                reference=component.reference,
                kind=component.kind if component.kind != "unknown" else component.symbol,
                symbol=component.symbol,
                value=component.value,
                description=component.description,
                nodes=tuple(
                    net_names[pin.point]
                    for pin in sorted(component.pins, key=lambda item: item.order)
                ),
                parameters=parameters,
                raw_parameter_lines=raw_parameter_lines,
                position_x=component.anchor[0],
                position_y=component.anchor[1],
                rotation_degrees=_rotation_degrees(component.rotation_code),
                has_subcircuit=component.kind.upper() == "X" or component.symbol.upper() == "X",
            )
        )
    return tuple(inspections)


def _write_artifact(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    if not destination.is_file():
        raise ArtifactMissingError(f"Schematic creation did not produce an artifact: {destination}")


def blank_schematic_bytes() -> bytes:
    return _QSCH_FILE_PREFIX + _tag_inline(0, b"schematic") + _QSCH_NEWLINE


def write_blank_schematic(destination: Path) -> None:
    _write_artifact(destination, blank_schematic_bytes())


def _voltage_source_component_bytes(reference: str, value: str) -> bytes:
    lines = [
        _tag_open(2, b"component (400,400) 0 0"),
        _tag_open(4, b"symbol V"),
        _tag_inline(6, b"type: V"),
        _tag_inline(6, b"description: Independent Voltage Source"),
        _tag_inline(6, b"shorted pins: false"),
        _tag_inline(6, b"line (0,-130) (0,-200) 0 0 0x1000000 -1 -1"),
        _tag_inline(6, b"line (0,200) (0,130) 0 0 0x1000000 -1 -1"),
        _tag_inline(6, b"rect (-25,77) (25,73) 0 0 0 0x1000000 0x3000000 -1 0 -1"),
        _tag_inline(6, b"rect (-2,50) (2,100) 0 0 0 0x1000000 0x3000000 -1 0 -1"),
        _tag_inline(6, b"rect (-25,-73) (25,-77) 0 0 0 0x1000000 0x3000000 -1 0 -1"),
        _tag_inline(6, b"ellipse (-130,130) (130,-130) 0 0 0 0x1000000 0x1000000 -1 -1"),
        _tag_text(
            6,
            b"text (100,150) 1 7 0 0x1000000 -1 -1 ",
            reference,
            field_name="source_reference",
        ),
        _tag_text(
            6,
            b"text (100,-150) 1 7 0 0x1000000 -1 -1 ",
            value,
            field_name="source_value",
        ),
    ]
    lines.extend(
        [
            _tag_inline(6, b'pin (0,200) (0,0) 1 0 0 0x0 -1 "+"'),
            _tag_inline(6, b'pin (0,-200) (0,0) 1 0 0 0x0 -1 "-"'),
            _tag_close(4),
            _tag_close(2),
        ]
    )
    return b"".join(lines)


def _resistor_component_bytes(reference: str, value: str) -> bytes:
    lines = [
        _tag_open(2, b"component (800,400) 0 0"),
        _tag_open(4, b"symbol R"),
        _tag_inline(6, b"type: R"),
        _tag_inline(6, b"description: Resistor(USA Style Symbol)"),
        _tag_inline(6, b"shorted pins: false"),
        _tag_inline(6, b"line (0,200) (0,180) 0 0 0x1000000 -1 -1"),
        _tag_inline(6, b"line (0,-180) (0,-200) 0 0 0x1000000 -1 -1"),
        _tag_inline(6, b"zigzag (-80,180) (80,-180) 0 0 0 0x1000000 -1 -1"),
        _tag_text(
            6,
            b"text (100,150) 1 7 0 0x1000000 -1 -1 ",
            reference,
            field_name="load_reference",
        ),
        _tag_text(
            6,
            b"text (100,-150) 1 7 0 0x1000000 -1 -1 ",
            value,
            field_name="load_value",
        ),
    ]
    lines.extend(
        [
            _tag_inline(6, b'pin (0,200) (0,0) 1 0 0 0x0 -1 "1"'),
            _tag_inline(6, b'pin (0,-200) (0,0) 1 0 0 0x0 -1 "2"'),
            _tag_close(4),
            _tag_close(2),
        ]
    )
    return b"".join(lines)


def starter_schematic_bytes(
    *,
    source_reference: str,
    source_value: str | int | float | complex,
    load_reference: str,
    load_value: str | int | float | complex,
    output_net_name: str,
    analysis_instruction: str,
) -> bytes:
    normalized_source_reference = _component_reference(
        source_reference,
        field_name="source_reference",
    )
    normalized_load_reference = _component_reference(
        load_reference,
        field_name="load_reference",
    )
    if normalized_source_reference == normalized_load_reference:
        raise ValueError("source_reference and load_reference must be distinct.")

    normalized_source_value = str(source_value)
    normalized_load_value = str(load_value)
    normalized_output_net = _normalize_net_name(output_net_name)
    normalized_instruction = str(analysis_instruction).strip()
    if not normalized_instruction:
        raise ValueError("analysis_instruction must not be empty.")
    _quote_qsch_string(normalized_instruction)
    output_net_bytes = _quoted_utf8_bytes(
        normalized_output_net,
        field_name="output_net_name",
    )
    ground_net_bytes = _quoted_utf8_bytes(
        _GROUND_NET_NAME,
        field_name="ground_net_name",
    )

    lines = [
        _tag_open(0, b"schematic"),
        _voltage_source_component_bytes(normalized_source_reference, normalized_source_value),
        _resistor_component_bytes(normalized_load_reference, normalized_load_value),
        _tag_inline(2, b"wire (400,600) (800,600) " + output_net_bytes),
        _tag_inline(2, b"wire (400,200) (800,200) " + ground_net_bytes),
        _tag_inline(2, b"net (400,600) 1 14 0 " + output_net_bytes),
        _tag_inline(2, b"net (400,200) 1 13 0 " + ground_net_bytes),
        (b" " * 2)
        + _QSCH_OPEN
        + b"text (400,-40) 1 0 0 0x1000000 -1 -1 "
        + b'"'
        + _DIRECTIVE_UTF8_BOM
        + normalized_instruction.encode("utf-8")
        + b'"'
        + _QSCH_CLOSE
        + _QSCH_NEWLINE,
        _tag_close(0),
        _QSCH_NEWLINE,
    ]
    return _QSCH_FILE_PREFIX + b"".join(lines)


def write_starter_schematic(
    destination: Path,
    *,
    source_reference: str,
    source_value: str | int | float | complex,
    load_reference: str,
    load_value: str | int | float | complex,
    output_net_name: str,
    analysis_instruction: str,
) -> None:
    _write_artifact(
        destination,
        starter_schematic_bytes(
            source_reference=source_reference,
            source_value=source_value,
            load_reference=load_reference,
            load_value=load_value,
            output_net_name=output_net_name,
            analysis_instruction=analysis_instruction,
        ),
    )


__all__ = [
    "CleanRoomComponentInspection",
    "add_instruction_to_supported_schematic",
    "blank_schematic_bytes",
    "inspect_supported_schematic_components",
    "remove_instruction_from_supported_schematic",
    "starter_schematic_bytes",
    "write_blank_schematic",
    "write_starter_schematic",
]
