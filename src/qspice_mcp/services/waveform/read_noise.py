"""Service for parsing QSpice `.noise` summaries from log files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_LOG_SUFFIXES = (".log",)
_FLOAT_TOKEN = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_INTEGRATED_NOISE = re.compile(
    rf"(?P<label>Total(?:\s+(?:RMS|Integrated))?\s+Noise(?:\s+Voltage|\s+Current)?"
    rf"(?:\s+at\s+(?P<node>[^\s=]+))?)\s*=?\s*(?P<value>{_FLOAT_TOKEN})\s*(?P<unit>\S+)?",
    re.IGNORECASE,
)
_SPECTRAL_NOISE = re.compile(
    rf"(?P<label>(?:Output|Input\s+Referred)\s+noise(?:\s+at\s+(?P<frequency>{_FLOAT_TOKEN}\s*\S+))?)"
    rf"\s*=?\s*(?P<value>{_FLOAT_TOKEN})\s*(?P<unit>\S+)?",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class NoiseSummary:
    """One integrated or spot noise value parsed from a simulation log."""

    label: str
    value: float
    unit: str
    node: str | None = None
    frequency: str | None = None


@dataclass(frozen=True, slots=True)
class NoiseLogInspection:
    """Parsed `.noise` summary rows from one simulation log."""

    log_path: Path
    summaries: tuple[NoiseSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="read_noise",
    title="Read Noise Analysis",
    summary="Parse integrated and spot `.noise` summary lines from a simulation `.log` file.",
    phase="implemented",
    read_only=True,
)


def _parse_float(token: str) -> float:
    return float(token.replace("d", "e").replace("D", "E"))


def parse_noise_log_text(
    log_path: Path,
    text: str,
) -> NoiseLogInspection:
    """Parse `.noise` summary lines from one log body."""

    summaries: list[NoiseSummary] = []
    seen_labels: set[str] = set()
    for line in text.replace("\r\n", "\n").split("\n"):
        for pattern in (_INTEGRATED_NOISE, _SPECTRAL_NOISE):
            match = pattern.search(line)
            if match is None:
                continue
            label = " ".join(match.group("label").split())
            if label in seen_labels:
                break
            seen_labels.add(label)
            unit = (match.group("unit") or "").strip()
            node = match.groupdict().get("node")
            frequency = match.groupdict().get("frequency")
            summaries.append(
                NoiseSummary(
                    label=label,
                    value=_parse_float(match.group("value")),
                    unit=unit,
                    node=node.strip() if isinstance(node, str) else None,
                    frequency=frequency.strip() if isinstance(frequency, str) else None,
                )
            )
            break

    warnings: tuple[str, ...] = ()
    if not summaries:
        warnings = ("No `.noise` summary lines were found in the log.",)
    return NoiseLogInspection(log_path=log_path, summaries=tuple(summaries), warnings=warnings)


def read_noise(
    log_path: str | Path,
    *,
    workspace_root: Path,
) -> NoiseLogInspection:
    """Read `.noise` summary lines from one simulation log."""

    resolved_log = validate_existing_file(
        log_path,
        workspace_root=workspace_root.resolve(strict=False),
        suffixes=_LOG_SUFFIXES,
    )
    text = resolved_log.read_text(encoding="utf-8", errors="replace")
    return parse_noise_log_text(resolved_log, text)


__all__ = [
    "SERVICE_SPEC",
    "NoiseLogInspection",
    "NoiseSummary",
    "parse_noise_log_text",
    "read_noise",
]
