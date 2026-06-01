"""Domain models. Frozen dataclasses, no I/O dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import numpy as np
    from numpy.typing import NDArray


class AnalysisKind(StrEnum):
    """Supported analysis types."""

    TRAN = "tran"
    AC = "ac"
    DC = "dc"
    OP = "op"
    NOISE = "noise"
    TF = "tf"
    STEP = "step"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Component:
    """A single SPICE element line, parsed."""

    refdes: str
    kind: str
    nodes: tuple[str, ...]
    value: str
    params: dict[str, str] = field(default_factory=dict)
    raw_line: str = ""

    def __post_init__(self) -> None:
        if not self.refdes:
            raise ValueError("Component must have a reference designator")


@dataclass(frozen=True, slots=True)
class Analysis:
    """A parsed analysis directive such as `.tran 0 1m`."""

    kind: AnalysisKind
    params: dict[str, str | float] = field(default_factory=dict)
    raw: str = ""


@dataclass(frozen=True, slots=True)
class Netlist:
    """Parsed netlist representation."""

    title: str
    components: list[Component]
    directives: list[str]
    analyses: list[Analysis]
    raw: str

    def find(self, refdes: str) -> Component | None:
        """Find a component by reference designator, case-insensitively."""
        for component in self.components:
            if component.refdes.lower() == refdes.lower():
                return component
        return None


@dataclass(frozen=True, slots=True)
class Waveform:
    """A single signal trace, possibly downsampled."""

    name: str
    x: NDArray[np.float64]
    y: NDArray[np.float64] | NDArray[np.complex128]
    x_unit: str = "s"
    y_unit: str = "V"
    complex_data: bool = False
    downsampled: bool = False
    original_length: int | None = None


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Outcome of a simulator run."""

    run_id: str
    raw_path: Path
    log_path: Path
    analysis: Analysis
    signals: list[str]
    duration_s: float
    exit_code: int
    cached: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now().astimezone())
