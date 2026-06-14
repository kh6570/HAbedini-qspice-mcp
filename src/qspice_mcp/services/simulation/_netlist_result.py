"""Shared result types for netlist generation.

Kept dependency-free so both ``generate_netlist`` and the QUX companion
module can import the types without introducing an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

NetlistBackend = Literal["qux", "clean_room", "editor", "existing"]


@dataclass(frozen=True, slots=True)
class GeneratedNetlist:
    """Resolved or staged netlist artifact metadata."""

    source_path: Path
    netlist_path: Path
    source_kind: Literal["schematic", "netlist"]
    refreshed: bool
    copied: bool
    warnings: tuple[str, ...] = ()
    netlist_backend: NetlistBackend | None = None


__all__ = ["GeneratedNetlist", "NetlistBackend"]
