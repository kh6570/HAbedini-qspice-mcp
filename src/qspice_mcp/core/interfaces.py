"""Protocols that adapters must implement. The dependency boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from .models import Analysis, Netlist, SimulationResult, Waveform


@runtime_checkable
class Simulator(Protocol):
    """Anything that can run a netlist and produce a SimulationResult."""

    async def run(
        self,
        netlist_path: Path,
        *,
        timeout_s: float,
        workdir: Path,
        run_id: str,
    ) -> SimulationResult: ...

    async def cancel(self, run_id: str) -> None: ...


@runtime_checkable
class RawHandle(Protocol):
    """An open .qraw file."""

    @property
    def signals(self) -> list[str]: ...

    @property
    def analysis(self) -> Analysis: ...

    @property
    def n_points(self) -> int: ...

    def read(
        self,
        signal: str,
        *,
        t_start: float | None = None,
        t_end: float | None = None,
        max_points: int = 2000,
    ) -> Waveform: ...

    def close(self) -> None: ...

    def __enter__(self) -> RawHandle: ...

    def __exit__(self, *exc: object) -> None: ...


@runtime_checkable
class RawReader(Protocol):
    """Factory for RawHandle instances."""

    def can_read(self, path: Path) -> bool: ...

    def open(self, path: Path) -> RawHandle: ...


@runtime_checkable
class NetlistParser(Protocol):
    """Parses and writes netlist text."""

    def parse(self, text: str) -> Netlist: ...

    def write(self, netlist: Netlist) -> str: ...
