"""Service for parsing native QSpice `.four` Fourier summaries from log files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_LOG_SUFFIXES = (".log",)
_FLOAT_PATTERN = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_SECTION_HEADER = re.compile(
    r"Fourier\s+(?:components?\s+of\s+(?:output\s+)?|analysis\s+(?:of\s+)?)?"
    r"(?:transient\s+response\s+of\s+)?(?P<node>[^\n:]+)",
    re.IGNORECASE,
)
_DC_COMPONENT = re.compile(
    rf"DC\s+component\s*=?\s*(?P<value>{_FLOAT_PATTERN})",
    re.IGNORECASE,
)
_THD_LINE = re.compile(
    rf"Total\s+Harmonic\s+Distortion\s*:?\s*(?P<value>{_FLOAT_PATTERN})\s*%?",
    re.IGNORECASE,
)
_HARMONIC_ROW = re.compile(
    rf"^\s*(?P<harmonic>\d+)\s+(?P<frequency>{_FLOAT_PATTERN})\s+"
    rf"(?P<magnitude>{_FLOAT_PATTERN})\s+(?P<phase>{_FLOAT_PATTERN})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FourierHarmonic:
    """One harmonic row from a native `.four` log summary."""

    harmonic: int
    frequency_hz: float
    magnitude: float
    phase_deg: float


@dataclass(frozen=True, slots=True)
class FourierAnalysis:
    """Parsed native `.four` summary for one node or expression."""

    log_path: Path
    node: str
    dc_component: float | None
    total_harmonic_distortion_pct: float | None
    harmonics: tuple[FourierHarmonic, ...]


@dataclass(frozen=True, slots=True)
class FourierLogInspection:
    """All native `.four` summaries found in one simulation log."""

    log_path: Path
    analyses: tuple[FourierAnalysis, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="read_fourier",
    title="Read Fourier Analysis",
    summary=(
        "Parse native QSpice `.four` Fourier summaries from a simulation `.log` "
        "file (distinct from recomputed FFT tools)."
    ),
    phase="implemented",
    read_only=True,
)


def _parse_float(token: str) -> float:
    return float(token.replace("d", "e").replace("D", "E"))


def _parse_section(
    log_path: Path,
    *,
    node: str,
    lines: tuple[str, ...],
) -> FourierAnalysis:
    dc_component: float | None = None
    total_harmonic_distortion_pct: float | None = None
    harmonics: list[FourierHarmonic] = []
    for line in lines:
        dc_match = _DC_COMPONENT.search(line)
        if dc_match is not None:
            dc_component = _parse_float(dc_match.group("value"))
            continue
        thd_match = _THD_LINE.search(line)
        if thd_match is not None:
            total_harmonic_distortion_pct = _parse_float(thd_match.group("value"))
            continue
        harmonic_match = _HARMONIC_ROW.match(line)
        if harmonic_match is not None:
            harmonics.append(
                FourierHarmonic(
                    harmonic=int(harmonic_match.group("harmonic")),
                    frequency_hz=_parse_float(harmonic_match.group("frequency")),
                    magnitude=_parse_float(harmonic_match.group("magnitude")),
                    phase_deg=_parse_float(harmonic_match.group("phase")),
                )
            )
    return FourierAnalysis(
        log_path=log_path,
        node=node.strip(),
        dc_component=dc_component,
        total_harmonic_distortion_pct=total_harmonic_distortion_pct,
        harmonics=tuple(harmonics),
    )


def parse_fourier_log_text(
    log_path: Path,
    text: str,
) -> FourierLogInspection:
    """Parse all `.four` sections from one log body."""

    lines = tuple(text.replace("\r\n", "\n").split("\n"))
    analyses: list[FourierAnalysis] = []
    current_node: str | None = None
    current_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_node, current_lines
        if current_node is None:
            current_lines = []
            return
        analyses.append(_parse_section(log_path, node=current_node, lines=tuple(current_lines)))
        current_node = None
        current_lines = []

    for line in lines:
        header_match = _SECTION_HEADER.search(line)
        if header_match is not None:
            flush_section()
            current_node = header_match.group("node").strip()
            current_lines = [line]
            continue
        if current_node is not None:
            if line.strip() == "" and current_lines and not current_lines[-1].strip():
                flush_section()
                continue
            current_lines.append(line)
    flush_section()

    warnings: tuple[str, ...] = ()
    if not analyses:
        warnings = ("No native `.four` Fourier summaries were found in the log.",)
    return FourierLogInspection(log_path=log_path, analyses=tuple(analyses), warnings=warnings)


def read_fourier(
    log_path: str | Path,
    *,
    workspace_root: Path,
) -> FourierLogInspection:
    """Read native `.four` Fourier summaries from one simulation log."""

    resolved_log = validate_existing_file(
        log_path,
        workspace_root=workspace_root.resolve(strict=False),
        suffixes=_LOG_SUFFIXES,
    )
    text = resolved_log.read_text(encoding="utf-8", errors="replace")
    return parse_fourier_log_text(resolved_log, text)


__all__ = [
    "SERVICE_SPEC",
    "FourierAnalysis",
    "FourierHarmonic",
    "FourierLogInspection",
    "parse_fourier_log_text",
    "read_fourier",
]
