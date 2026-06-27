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

# Bump whenever the log-classification rulesets below change. Contract tests
# pin this value so behavior changes are deliberate and reviewable.
LOG_CLASSIFICATION_VERSION = 2

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
# Lines matching an ignore pattern are never classified as failures even when
# they also match a convergence/fatal pattern. Real local QSpice builds emit
# recoverable diagnostics (for example "Warning: Singular matrix. Check node A"
# followed by successful Gmin stepping) that must not abort a passing run.
_IGNORE_PATTERNS = (re.compile(r"^\s*warning\b", re.IGNORECASE),)


@dataclass(frozen=True, slots=True)
class _LogRuleSet:
    """Resolved convergence/fatal/ignore patterns for one QSpice build."""

    convergence: tuple[re.Pattern[str], ...]
    fatal: tuple[re.Pattern[str], ...]
    ignore: tuple[re.Pattern[str], ...]


@dataclass(frozen=True, slots=True)
class _LogRuleOverride:
    """Version-specific additions layered on top of the base rule set."""

    extra_convergence: tuple[re.Pattern[str], ...] = ()
    extra_fatal: tuple[re.Pattern[str], ...] = ()
    extra_ignore: tuple[re.Pattern[str], ...] = ()


_BASE_LOG_RULES = _LogRuleSet(
    convergence=_CONVERGENCE_PATTERNS,
    fatal=_FATAL_PATTERNS,
    ignore=_IGNORE_PATTERNS,
)

# Convergence/fatal regex overrides keyed by ``ProbeResult.version``. Seeded with
# the QSpice build whose real log corpus is captured under
# ``tests/data/qspice_logs/`` and pinned by the adapter contract tests. Newly
# observed build-specific signatures are added here without touching the base.
_VERSION_LOG_OVERRIDES: dict[str, _LogRuleOverride] = {
    # QSpice 2026-06-04 build: the base rule set (with the recoverable-warning
    # skip) classifies its real healthy/fatal/singular logs correctly, so no
    # extra signatures are required. Recorded as an explicit, tested key.
    "20260604": _LogRuleOverride(),
}


def resolve_log_rules(version: str | None) -> _LogRuleSet:
    """Return the base log rule set merged with any version-specific overrides."""

    override = _VERSION_LOG_OVERRIDES.get(version) if version is not None else None
    if override is None:
        return _BASE_LOG_RULES
    return _LogRuleSet(
        convergence=_BASE_LOG_RULES.convergence + override.extra_convergence,
        fatal=_BASE_LOG_RULES.fatal + override.extra_fatal,
        ignore=_BASE_LOG_RULES.ignore + override.extra_ignore,
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


def _match_failure_line(log_text: str, rules: _LogRuleSet) -> tuple[str, str] | None:
    """Return the first clear failure line from the simulation log."""

    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in rules.ignore):
            continue
        if any(pattern.search(line) for pattern in rules.convergence):
            return ("convergence", line)
        if any(pattern.search(line) for pattern in rules.fatal):
            return ("fatal", line)
    return None


@dataclass(frozen=True, slots=True)
class CurrentQSpiceCLIAdapter:
    """Conservative adapter for the currently installed QSpice CLI."""

    key: str = "cli.v1"
    title: str = "Current QSpice CLI"
    capabilities: AdapterCapabilities = field(default_factory=_default_capabilities)
    log_classification_version: int = LOG_CLASSIFICATION_VERSION

    def can_handle(self, probe: ProbeResult) -> bool:
        """Return whether the discovered executable can be used by this adapter."""

        return probe.executable is not None and probe.exists

    def supports_probe_version(self, version: str | None) -> bool:
        """Return whether this adapter's log rules apply to a probed version.

        Version-specific adapters should override this seam so the registry can
        prefer them for matching QSpice releases. The conservative ``cli.v1``
        adapter applies to every discovered version as the baseline fallback.
        """

        del version
        return True

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
        probe_version: str | None = None,
    ) -> SimulationError | None:
        """Map clear log-level failures to domain exceptions.

        ``probe_version`` selects any version-specific regex overrides for the
        QSpice build that produced the log; ``None`` uses the base rule set.
        """

        rules = resolve_log_rules(probe_version)
        matched = _match_failure_line(log_text, rules)
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
