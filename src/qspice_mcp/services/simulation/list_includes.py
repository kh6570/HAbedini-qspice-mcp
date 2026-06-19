"""List include and library directives referenced by a netlist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._netlist_includes import collect_netlist_includes

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class IncludeSummary:
    """One include or library directive discovered in a netlist graph."""

    kind: str
    directive: str
    raw_path: str
    resolved_path: Path | None
    exists: bool
    source_netlist: Path


@dataclass(frozen=True, slots=True)
class IncludeCatalog:
    """Include/library inventory for one netlist root."""

    netlist_path: Path
    include_count: int
    missing_count: int
    includes: tuple[IncludeSummary, ...]


SERVICE_SPEC = ServiceSpec(
    name="list_includes",
    title="List Netlist Includes",
    summary="List `.include`, `.inc`, and `.lib` directives reachable from one netlist.",
    phase="implemented",
    read_only=True,
)


def list_includes(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
) -> IncludeCatalog:
    """Return every include/library directive reachable from one netlist."""

    normalized_workspace = workspace_root.resolve(strict=False)
    root = validate_existing_file(
        netlist_path,
        workspace_root=normalized_workspace,
        suffixes=(".net", ".cir", ".inc"),
    )
    includes = collect_netlist_includes(root, workspace_root=normalized_workspace)
    summaries = tuple(
        IncludeSummary(
            kind=entry.kind,
            directive=entry.directive,
            raw_path=entry.raw_path,
            resolved_path=entry.resolved_path,
            exists=entry.exists,
            source_netlist=entry.source_netlist,
        )
        for entry in includes
    )
    missing_count = sum(1 for entry in summaries if not entry.exists)
    return IncludeCatalog(
        netlist_path=root,
        include_count=len(summaries),
        missing_count=missing_count,
        includes=summaries,
    )


__all__ = ["SERVICE_SPEC", "IncludeCatalog", "IncludeSummary", "list_includes"]
