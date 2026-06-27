"""Service for lightweight schematic inspection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.core.models import Analysis, AnalysisKind
from qspice_mcp.services._backends._qsch_editor import (
    _QCLOSE,
    _QOPEN,
    _QSCH_BINARY_PREFIX,
    _decode_qsch_bytes,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic.read_net_connectivity import (
    NetConnectivityReport,
    read_net_connectivity,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_QUOTED_TEXT_PATTERN = re.compile(r'"([^"]*)"')
_ANALYSIS_ORDER: tuple[AnalysisKind, ...] = (
    AnalysisKind.TRAN,
    AnalysisKind.AC,
    AnalysisKind.DC,
    AnalysisKind.OP,
    AnalysisKind.NOISE,
    AnalysisKind.TF,
    AnalysisKind.STEP,
)
_ATTRIBUTE_TEXT_START = 2


@dataclass(frozen=True, slots=True)
class SchematicComponentSummary:
    """A lightweight summary of one schematic component."""

    refdes: str
    symbol: str
    kind: str
    value: str | None = None
    description: str | None = None
    library_file: str | None = None
    attributes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class SchematicInspection:
    """Summary produced by the inspect_schematic service."""

    schematic_path: Path
    title: str
    component_count: int
    components: tuple[SchematicComponentSummary, ...]
    analyses: tuple[Analysis, ...]
    format_hint: str | None
    line_count: int
    size_bytes: int
    parameters: tuple[str, ...] = field(default_factory=tuple)
    connectivity: NetConnectivityReport | None = None


class _ComponentAccumulator(TypedDict, total=False):
    texts: list[str]
    symbol: str
    kind: str
    description: str
    library_file: str


SERVICE_SPEC = ServiceSpec(
    name="inspect_schematic",
    title="Inspect Schematic",
    summary="Summarize a .qsch file and its configured analyses before simulation.",
    phase="implemented",
)


def _decode_inspection_bytes(raw_bytes: bytes) -> str:
    """Decode schematic bytes using the same qsch text rules as editor backends."""

    payload = raw_bytes
    if payload.startswith(_QSCH_BINARY_PREFIX):
        payload = payload[len(_QSCH_BINARY_PREFIX) :]
    return _decode_qsch_bytes(payload)


def _clean_line(raw_line: str) -> str:
    """Remove replacement characters, guillemets, and surrounding whitespace."""

    cleaned = raw_line.replace("\ufffd", "").replace("\x00", "").strip()
    if cleaned.startswith(_QOPEN):
        cleaned = cleaned[len(_QOPEN) :].strip()
    if cleaned.endswith(_QCLOSE):
        cleaned = cleaned[: -len(_QCLOSE)].strip()
    return cleaned


def _extract_quoted_text(line: str) -> str | None:
    """Extract the first quoted text payload from a schematic line."""

    match = _QUOTED_TEXT_PATTERN.search(line)
    return match.group(1) if match is not None else None


@dataclass(frozen=True, slots=True)
class SchematicContentInspection:
    """Summary produced from raw schematic bytes without a workspace path."""

    component_count: int
    components: tuple[SchematicComponentSummary, ...]
    analyses: tuple[Analysis, ...]
    parameters: tuple[str, ...]
    size_bytes: int


def _extract_parameters(lines: tuple[str, ...]) -> tuple[str, ...]:
    """Extract schematic-level `.param` directives from sanitized lines."""

    parameters: list[str] = []
    seen: set[str] = set()
    for line in lines:
        lowered = line.lower()
        marker = ".param"
        if marker not in lowered:
            continue
        start_index = lowered.index(marker)
        raw = line[start_index:].strip().strip('"')
        if raw not in seen:
            seen.add(raw)
            parameters.append(raw)
    return tuple(parameters)


def _extract_analyses(lines: tuple[str, ...]) -> tuple[Analysis, ...]:
    """Extract analysis directives from sanitized schematic lines."""

    analyses: list[Analysis] = []
    seen: set[tuple[AnalysisKind, str]] = set()
    for line in lines:
        lowered = line.lower()
        for kind in _ANALYSIS_ORDER:
            marker = f".{kind.value}"
            if marker not in lowered:
                continue
            start_index = lowered.index(marker)
            raw = line[start_index:].strip().strip('"')
            key = (kind, raw)
            if key not in seen:
                seen.add(key)
                analyses.append(Analysis(kind=kind, raw=raw))
            break
    return tuple(analyses)


def _finalize_component(
    components: list[SchematicComponentSummary],
    current: _ComponentAccumulator | None,
) -> None:
    """Finalize the current component accumulator if present."""

    if current is None:
        return

    texts = tuple(current["texts"])
    refdes = texts[0] if texts else f"component_{len(components) + 1}"
    value = texts[1] if len(texts) > 1 else None
    attributes = texts[_ATTRIBUTE_TEXT_START:] if len(texts) > _ATTRIBUTE_TEXT_START else ()
    symbol = str(current.get("symbol") or "unknown")
    kind = str(current.get("kind") or symbol)
    description = current.get("description")
    library_file = current.get("library_file")
    components.append(
        SchematicComponentSummary(
            refdes=refdes,
            symbol=symbol,
            kind=kind,
            value=value,
            description=str(description) if description is not None else None,
            library_file=str(library_file) if library_file is not None else None,
            attributes=attributes,
        )
    )


def _extract_components(lines: tuple[str, ...]) -> tuple[SchematicComponentSummary, ...]:
    """Extract lightweight component summaries from sanitized schematic lines."""

    components: list[SchematicComponentSummary] = []
    current: _ComponentAccumulator | None = None
    for line in lines:
        if not line:
            continue
        if line.startswith("component "):
            _finalize_component(components, current)
            current = _ComponentAccumulator(texts=[])
            continue
        if current is None:
            continue
        if line.startswith("symbol "):
            current["symbol"] = line.removeprefix("symbol ").strip()
            continue
        if line.startswith("type:"):
            current["kind"] = line.partition(":")[2].strip()
            continue
        if line.startswith("description:"):
            current["description"] = line.partition(":")[2].strip()
            continue
        if line.startswith("library file:"):
            current["library_file"] = line.partition(":")[2].strip()
            continue
        if line.startswith("text "):
            value = _extract_quoted_text(line)
            if value is not None:
                current["texts"].append(value)
    _finalize_component(components, current)
    return tuple(components)


def inspect_schematic_bytes(raw_bytes: bytes) -> SchematicContentInspection:
    """Inspect schematic bytes with the same conservative text-scanning pass."""

    text = _decode_inspection_bytes(raw_bytes)
    cleaned_lines = tuple(_clean_line(line) for line in text.splitlines())
    components = _extract_components(cleaned_lines)
    analyses = _extract_analyses(cleaned_lines)
    parameters = _extract_parameters(cleaned_lines)
    return SchematicContentInspection(
        component_count=len(components),
        components=components,
        analyses=analyses,
        parameters=parameters,
        size_bytes=len(raw_bytes),
    )


def _maybe_read_connectivity(
    schematic_path: Path,
    *,
    workspace_root: Path,
) -> NetConnectivityReport | None:
    """Best-effort connectivity read; returns None when the schematic is unsupported."""

    try:
        return read_net_connectivity(schematic_path, workspace_root=workspace_root)
    except (QSpiceError, ValueError, OSError):
        return None


def inspect_schematic(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    include_connectivity: bool = False,
    include_parameters: bool = False,
) -> SchematicInspection:
    """Inspect a `.qsch` file with a conservative text-scanning pass.

    Optional sections fold in detail that otherwise needs separate read calls:
    ``include_parameters`` surfaces schematic-level ``.param`` directives, and
    ``include_connectivity`` attaches the net-to-pin connectivity report.
    """

    schematic_path = validate_existing_file(
        raw_path,
        workspace_root=workspace_root,
        suffixes=(".qsch",),
    )
    raw_bytes = schematic_path.read_bytes()
    content = inspect_schematic_bytes(raw_bytes)
    cleaned_lines = tuple(
        _clean_line(line) for line in _decode_inspection_bytes(raw_bytes).splitlines()
    )
    non_empty_lines = tuple(line for line in cleaned_lines if line)
    format_hint = non_empty_lines[0] if non_empty_lines else None
    connectivity = (
        _maybe_read_connectivity(schematic_path, workspace_root=workspace_root)
        if include_connectivity
        else None
    )
    return SchematicInspection(
        schematic_path=schematic_path,
        title=schematic_path.stem,
        component_count=content.component_count,
        components=content.components,
        analyses=content.analyses,
        format_hint=format_hint,
        line_count=len(cleaned_lines),
        size_bytes=content.size_bytes,
        parameters=content.parameters if include_parameters else (),
        connectivity=connectivity,
    )


__all__ = [
    "SERVICE_SPEC",
    "SchematicComponentSummary",
    "SchematicContentInspection",
    "SchematicInspection",
    "inspect_schematic",
    "inspect_schematic_bytes",
]
