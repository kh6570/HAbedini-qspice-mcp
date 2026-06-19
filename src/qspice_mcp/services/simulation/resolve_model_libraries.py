"""Resolve model library paths referenced by a netlist."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._netlist_includes import collect_netlist_includes

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ResolvedModelLibrary:
    """One resolved `.lib` path referenced by a netlist graph."""

    raw_path: str
    resolved_path: Path | None
    exists: bool
    source_netlist: Path


@dataclass(frozen=True, slots=True)
class ModelLibraryResolution:
    """Resolved model-library paths for one netlist root."""

    netlist_path: Path
    library_count: int
    missing_count: int
    libraries: tuple[ResolvedModelLibrary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="resolve_model_libraries",
    title="Resolve Model Libraries",
    summary="Resolve `.lib` model-library paths referenced by one netlist.",
    phase="implemented",
    read_only=True,
)


def resolve_model_libraries(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
) -> ModelLibraryResolution:
    """Resolve every `.lib` directive reachable from one netlist."""

    normalized_workspace = workspace_root.resolve(strict=False)
    root = validate_existing_file(
        netlist_path,
        workspace_root=normalized_workspace,
        suffixes=(".net", ".cir", ".inc"),
    )
    includes = collect_netlist_includes(root, workspace_root=normalized_workspace)
    libraries = tuple(
        ResolvedModelLibrary(
            raw_path=entry.raw_path,
            resolved_path=entry.resolved_path,
            exists=entry.exists,
            source_netlist=entry.source_netlist,
        )
        for entry in includes
        if entry.kind == "lib"
    )
    missing = tuple(library.raw_path for library in libraries if not library.exists)
    warnings: tuple[str, ...] = ()
    if missing:
        warnings = (f"Missing model libraries: {', '.join(missing)}",)
    return ModelLibraryResolution(
        netlist_path=root,
        library_count=len(libraries),
        missing_count=len(missing),
        libraries=libraries,
        warnings=warnings,
    )


__all__ = [
    "SERVICE_SPEC",
    "ModelLibraryResolution",
    "ResolvedModelLibrary",
    "resolve_model_libraries",
]
