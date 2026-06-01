"""Current QSpice CLI adapter bootstrap."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import (
    AdapterNotFoundError,
    ConvergenceError,
    SimulationError,
    ValidationError,
)

from ..base import AdapterCapabilities, AdapterDescription, SimulationCommand

if TYPE_CHECKING:
    from pathlib import Path

    from ..probe import ProbeResult

_SUPPORTED_NETLIST_SUFFIXES = frozenset({".cir", ".net"})
_RESERVED_SWITCHES = frozenset({"-o", "-r"})
_PATHLIKE_SWITCH_MARKERS = ("\\", "/", ":")
_CONVERGENCE_PATTERNS = (
    re.compile(r"\b(?:time\s*step|timestep)\s+too\s+small\b", re.IGNORECASE),
    re.compile(r"\binternal\s+timestep\s+too\s+small\b", re.IGNORECASE),
    re.compile(r"\b(?:no\s+convergence|failed\s+to\s+converge)\b", re.IGNORECASE),
    re.compile(r"\bconvergence\s+(?:problem|failure)\b", re.IGNORECASE),
    re.compile(r"\biteration\s+limit\s+reached\b", re.IGNORECASE),
    re.compile(r"\bsingular\s+matrix\b", re.IGNORECASE),
    re.compile(r"\btrouble\s+with\s+node\b", re.IGNORECASE),
)
_FATAL_PATTERNS = (
    re.compile(r"\bfatal\s+error\b", re.IGNORECASE),
    re.compile(r"^\s*error\b", re.IGNORECASE),
)


def _default_capabilities() -> AdapterCapabilities:
    return AdapterCapabilities(
        probe=True,
        cli_invocation=True,
        schematic_inspection=False,
        netlist_generation=False,
        qraw_reading=False,
        notes=(
            "Executable selection and .cir/.net simulation command construction are implemented.",
            "Schematic-to-netlist CLI behavior still needs confirmation before it is implemented.",
        ),
    )


def _normalize_path(path: Path) -> Path:
    """Return an absolute path without requiring it to exist already."""

    return path.expanduser().resolve(strict=False)


def _normalize_netlist_file(netlist_file: Path) -> Path:
    """Return a normalized simulation input path for supported netlist files."""

    normalized = _normalize_path(netlist_file)
    if normalized.suffix.lower() not in _SUPPORTED_NETLIST_SUFFIXES:
        raise ValueError("Current QSpice CLI adapter only supports .cir or .net simulation inputs.")
    return normalized


def _normalize_extra_switches(extra_switches: tuple[str, ...]) -> tuple[str, ...]:
    """Reject reserved output switches while preserving caller-provided order."""

    normalized: list[str] = []
    for switch in extra_switches:
        token = switch.strip()
        if not token:
            continue
        if not token.startswith("-"):
            raise ValidationError(
                "extra_switches only supports standalone dash-prefixed flags; "
                "positional arguments are not allowed."
            )
        if token.lower() in _RESERVED_SWITCHES:
            raise ValidationError(
                f"Switch {token} is managed by the adapter and cannot be passed explicitly."
            )
        if any(marker in token[1:] for marker in _PATHLIKE_SWITCH_MARKERS):
            raise ValidationError(
                "extra_switches cannot include path-like values or directory separators."
            )
        normalized.append(token)
    return tuple(normalized)


def _combine_diagnostics(stderr: str, matched_line: str) -> str:
    """Merge stderr and the decisive log line without duplicating information."""

    cleaned_stderr = stderr.strip()
    cleaned_line = matched_line.strip()
    if not cleaned_stderr:
        return cleaned_line
    if cleaned_line.lower() in cleaned_stderr.lower():
        return cleaned_stderr
    return f"{cleaned_stderr}\n{cleaned_line}"


def _match_failure_line(log_text: str) -> tuple[str, str] | None:
    """Return the first clear failure line from the simulation log."""

    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in _CONVERGENCE_PATTERNS):
            return ("convergence", line)
        if any(pattern.search(line) for pattern in _FATAL_PATTERNS):
            return ("fatal", line)
    return None


@dataclass(frozen=True, slots=True)
class CurrentQSpiceCLIAdapter:
    """Conservative adapter for the currently installed QSpice CLI."""

    key: str = "cli.v1"
    title: str = "Current QSpice CLI"
    capabilities: AdapterCapabilities = field(default_factory=_default_capabilities)

    def can_handle(self, probe: ProbeResult) -> bool:
        """Return whether the discovered executable can be used by this adapter."""

        return probe.executable is not None and probe.exists

    def describe(self, probe: ProbeResult) -> AdapterDescription:
        """Describe the adapter against the current probe result."""

        return AdapterDescription(
            key=self.key,
            title=self.title,
            available=self.can_handle(probe),
            executable=probe.executable,
            capabilities=self.capabilities,
        )

    def base_command(self, probe: ProbeResult) -> tuple[str, ...]:
        """Return the executable-only command prefix for later CLI composition."""

        if not self.can_handle(probe):
            raise AdapterNotFoundError("Current QSpice CLI adapter requires a valid executable.")
        assert probe.executable is not None
        return (str(probe.executable),)

    def classify_simulation_log(
        self,
        log_text: str,
        *,
        exit_code: int | None = None,
        stderr: str = "",
    ) -> SimulationError | None:
        """Map clear log-level failures to domain exceptions."""

        matched = _match_failure_line(log_text)
        if matched is None:
            return None

        failure_kind, matched_line = matched
        diagnostics = _combine_diagnostics(stderr, matched_line)
        if failure_kind == "convergence":
            return ConvergenceError(
                f"QSpice reported a convergence failure in the simulation log: {matched_line}",
                exit_code=exit_code,
                stderr=diagnostics,
            )
        return SimulationError(
            f"QSpice reported a fatal error in the simulation log: {matched_line}",
            exit_code=exit_code,
            stderr=diagnostics,
        )

    def build_simulation_command(
        self,
        probe: ProbeResult,
        netlist_file: Path,
        *,
        log_file: Path | None = None,
        raw_file: Path | None = None,
        extra_switches: tuple[str, ...] = (),
        ascii_raw: bool = False,
    ) -> SimulationCommand:
        """Build a concrete subprocess plan for running a netlist-based QSpice simulation."""

        normalized_netlist = _normalize_netlist_file(netlist_file)
        normalized_log = _normalize_path(log_file or normalized_netlist.with_suffix(".log"))
        normalized_raw = _normalize_path(raw_file or normalized_netlist.with_suffix(".qraw"))
        normalized_switches = _normalize_extra_switches(extra_switches)

        command: list[str] = [
            *self.base_command(probe),
            "-o",
            str(normalized_log),
            str(normalized_netlist),
        ]
        if raw_file is not None:
            command.extend(("-r", str(normalized_raw)))
        if ascii_raw:
            command.append("-ASCII")
        command.extend(normalized_switches)

        return SimulationCommand(
            command=tuple(command),
            working_directory=normalized_netlist.parent,
            netlist_file=normalized_netlist,
            log_file=normalized_log,
            raw_file=normalized_raw,
        )
