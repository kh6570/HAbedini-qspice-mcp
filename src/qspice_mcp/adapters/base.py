"""Base types for QSpice adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.core.exceptions import SimulationError

    from .probe import ProbeResult


@dataclass(frozen=True, slots=True)
class AdapterCapabilities:
    """Implemented capability surface of an adapter in this codebase."""

    probe: bool = True
    cli_invocation: bool = False
    schematic_inspection: bool = False
    netlist_generation: bool = False
    qraw_reading: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AdapterDescription:
    """JSON-friendly description of an adapter instance."""

    key: str
    title: str
    available: bool
    executable: Path | None
    capabilities: AdapterCapabilities

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable adapter summary."""

        return {
            "key": self.key,
            "title": self.title,
            "available": self.available,
            "executable": str(self.executable) if self.executable is not None else None,
            "capabilities": {
                "probe": self.capabilities.probe,
                "cli_invocation": self.capabilities.cli_invocation,
                "schematic_inspection": self.capabilities.schematic_inspection,
                "netlist_generation": self.capabilities.netlist_generation,
                "qraw_reading": self.capabilities.qraw_reading,
                "notes": list(self.capabilities.notes),
            },
        }


@dataclass(frozen=True, slots=True)
class SimulationCommand:
    """Concrete subprocess inputs and expected artifacts for a QSpice run."""

    command: tuple[str, ...]
    working_directory: Path
    netlist_file: Path
    log_file: Path
    raw_file: Path


@runtime_checkable
class QSpiceAdapter(Protocol):
    """Protocol implemented by concrete QSpice adapters."""

    key: str
    title: str
    capabilities: AdapterCapabilities

    def can_handle(self, probe: ProbeResult) -> bool: ...

    def describe(self, probe: ProbeResult) -> AdapterDescription: ...

    def base_command(self, probe: ProbeResult) -> tuple[str, ...]: ...

    def classify_simulation_log(
        self,
        log_text: str,
        *,
        exit_code: int | None = None,
        stderr: str = "",
    ) -> SimulationError | None: ...

    def build_simulation_command(
        self,
        probe: ProbeResult,
        netlist_file: Path,
        *,
        log_file: Path | None = None,
        raw_file: Path | None = None,
        extra_switches: tuple[str, ...] = (),
        ascii_raw: bool = False,
    ) -> SimulationCommand: ...
