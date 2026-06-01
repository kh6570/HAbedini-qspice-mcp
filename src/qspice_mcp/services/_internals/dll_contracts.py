"""Helpers for extracting `.DLL` symbol and source contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from qspice_mcp.core.exceptions import ValidationError

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import (
        ComponentSymbolMetadata,
        SymbolPinMetadata,
    )

DllPinDirection = Literal["input", "output"]

_DLL_COMPONENT_TYPE = "\u00d8(.DLL)"
_DLL_INPUT_PIN_KIND_CODE = 145
_DLL_OUTPUT_PIN_KIND_CODE = 146
_DLL_IDENTIFIER_RE = re.compile(r"[^0-9A-Za-z_]+")
_DLL_EXPORT_RE = re.compile(
    r'extern\s+"C"\s+__declspec\s*\(\s*dllexport\s*\)\s+'
    r"[A-Za-z_][A-Za-z0-9_\s\*]*?\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(",
    re.MULTILINE,
)
_DLL_PIN_MAPPING_RE = re.compile(
    r"^[^\n;]*?(?:&\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"data\[\s*(?P<index>\d+)\s*\]\.\w+\s*;\s*//\s*"
    r"(?P<direction>input|output)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_DLL_UNDEF_PIN_RE = re.compile(
    r"^\s*#undef\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class DllPinContract:
    """One ordered `.DLL` pin contract entry."""

    name: str
    direction: DllPinDirection
    data_index: int
    pin_kind_code: int | None = None


@dataclass(frozen=True, slots=True)
class DllSymbolContract:
    """Normalized `.DLL` contract derived from the schematic symbol."""

    reference: str
    device_name: str
    expected_export_name: str
    pins: tuple[DllPinContract, ...]

    @property
    def input_pin_names(self) -> tuple[str, ...]:
        return tuple(pin.name for pin in self.pins if pin.direction == "input")

    @property
    def output_pin_names(self) -> tuple[str, ...]:
        return tuple(pin.name for pin in self.pins if pin.direction == "output")


@dataclass(frozen=True, slots=True)
class DllSourceContract:
    """Normalized `.DLL` contract derived from one source file."""

    source_path: Path | None
    exported_function_names: tuple[str, ...]
    primary_export_name: str | None
    pins: tuple[DllPinContract, ...]
    warnings: tuple[str, ...]

    @property
    def input_pin_names(self) -> tuple[str, ...]:
        return tuple(pin.name for pin in self.pins if pin.direction == "input")

    @property
    def output_pin_names(self) -> tuple[str, ...]:
        return tuple(pin.name for pin in self.pins if pin.direction == "output")


def normalize_dll_identifier(raw_name: str) -> str:
    """Normalize one device or export name to a safe C-style identifier."""

    normalized = _DLL_IDENTIFIER_RE.sub("_", raw_name.strip()).strip("_")
    if not normalized:
        raise ValidationError("device_name must produce a non-empty DLL identifier.")
    if normalized[0].isdigit():
        raise ValidationError(
            "device_name must start with a letter and contain valid DLL identifier characters."
        )
    return normalized


def canonical_dll_identifier(raw_name: str) -> str:
    """Return a case-insensitive comparison form for one DLL identifier."""

    normalized = _DLL_IDENTIFIER_RE.sub("_", raw_name.strip()).strip("_")
    return normalized.lower()


def dll_pin_direction_from_symbol_pin(pin: SymbolPinMetadata) -> DllPinDirection:
    """Infer one `.DLL` pin direction from symbol metadata."""

    if pin.pin_kind_code == _DLL_OUTPUT_PIN_KIND_CODE:
        return "output"
    if pin.pin_kind_code == _DLL_INPUT_PIN_KIND_CODE:
        return "input"
    return "input" if pin.position_x < 0 else "output"


def build_dll_symbol_contract(
    *,
    reference: str,
    device_name: str,
    metadata: ComponentSymbolMetadata,
) -> DllSymbolContract:
    """Build one normalized `.DLL` contract from schematic symbol metadata."""

    if metadata.type_name != _DLL_COMPONENT_TYPE:
        raise ValidationError(
            f"Component {reference} is not a `.DLL` block; found type {metadata.type_name!r}."
        )

    normalized_device_name = device_name.strip()
    if not normalized_device_name:
        raise ValidationError(f"Component {reference} does not expose a DLL device name.")

    pins = tuple(
        DllPinContract(
            name=pin.name,
            direction=dll_pin_direction_from_symbol_pin(pin),
            data_index=index,
            pin_kind_code=pin.pin_kind_code,
        )
        for index, pin in enumerate(metadata.pins)
    )
    return DllSymbolContract(
        reference=reference,
        device_name=normalized_device_name,
        expected_export_name=normalize_dll_identifier(normalized_device_name),
        pins=pins,
    )


def parse_dll_source_contract_text(
    source_text: str,
    *,
    source_path: Path | None = None,
) -> DllSourceContract:
    """Parse exported entry points and `data[]` pin mappings from one source file."""

    exported_function_names = tuple(
        match.group("name") for match in _DLL_EXPORT_RE.finditer(source_text)
    )
    pin_matches = sorted(
        _DLL_PIN_MAPPING_RE.finditer(source_text),
        key=lambda match: int(match.group("index")),
    )

    warnings: list[str] = []
    if not exported_function_names:
        warnings.append('Source does not expose an `extern "C" __declspec(dllexport)` entry point.')

    pins = tuple(
        DllPinContract(
            name=match.group("name"),
            direction=cast("DllPinDirection", match.group("direction").lower()),
            data_index=int(match.group("index")),
        )
        for match in pin_matches
    )

    undef_pin_names = tuple(
        match.group("name") for match in _DLL_UNDEF_PIN_RE.finditer(source_text)
    )
    if not pins:
        if undef_pin_names:
            warnings.append(
                "Source exposes `#undef` pin names but no parseable `data[]` mappings "
                "with `// input` or `// output` comments."
            )
        else:
            warnings.append(
                "Source does not expose parseable `data[]` mappings with `// input` "
                "or `// output` comments."
            )

    seen_indexes: set[int] = set()
    duplicate_indexes = False
    for pin in pins:
        if pin.data_index in seen_indexes:
            duplicate_indexes = True
            break
        seen_indexes.add(pin.data_index)
    if duplicate_indexes:
        warnings.append("Source maps multiple pins to the same `data[]` index.")

    primary_export_name = exported_function_names[0] if exported_function_names else None
    return DllSourceContract(
        source_path=source_path,
        exported_function_names=exported_function_names,
        primary_export_name=primary_export_name,
        pins=pins,
        warnings=tuple(warnings),
    )


def find_matching_export_name(
    expected_export_name: str,
    exported_function_names: tuple[str, ...],
) -> str | None:
    """Return the source export that matches the symbol contract, if any."""

    expected = canonical_dll_identifier(expected_export_name)
    for function_name in exported_function_names:
        if canonical_dll_identifier(function_name) == expected:
            return function_name
    return None


__all__ = [
    "DllPinContract",
    "DllPinDirection",
    "DllSourceContract",
    "DllSymbolContract",
    "build_dll_symbol_contract",
    "canonical_dll_identifier",
    "dll_pin_direction_from_symbol_pin",
    "find_matching_export_name",
    "normalize_dll_identifier",
    "parse_dll_source_contract_text",
]
