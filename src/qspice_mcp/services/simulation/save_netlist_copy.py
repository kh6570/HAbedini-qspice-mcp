"""Explicit service for saving one derived netlist copy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation.generate_netlist import generate_netlist

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SavedNetlistCopy:
    """Metadata for one explicitly saved netlist copy."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    refreshed: bool
    copied: bool
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="save_netlist_copy",
    title="Save Netlist Copy",
    summary="Materialize one derived .net or .cir artifact at a requested destination.",
    phase="implemented",
    read_only=False,
)


def save_netlist_copy(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path,
) -> SavedNetlistCopy:
    """Resolve or generate one netlist artifact and persist it to an explicit path."""

    generated = generate_netlist(
        raw_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return SavedNetlistCopy(
        source_path=generated.source_path,
        output_path=generated.netlist_path,
        source_kind=generated.source_kind,
        refreshed=generated.refreshed,
        copied=generated.copied,
        warnings=generated.warnings,
    )


__all__ = ["SERVICE_SPEC", "SavedNetlistCopy", "save_netlist_copy"]
