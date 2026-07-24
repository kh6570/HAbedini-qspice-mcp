"""Service for staging a source with a documented `.save` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreparedSaveDirective:
    """Metadata for one source staged with a `.save` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_save",
    title="Prepare Save Directive",
    summary="Stage a schematic or netlist with a documented `.save` trace-limiting directive.",
    phase="implemented",
    read_only=False,
)


def prepare_save(
    source_path: str | Path,
    *,
    workspace_root: Path,
    patterns: Sequence[str],
    output_path: str | Path | None = None,
) -> PreparedSaveDirective:
    """Stage a source with one documented `.save` directive limiting stored traces."""

    normalized_patterns = tuple(pattern.strip() for pattern in patterns if pattern.strip())
    if not normalized_patterns:
        raise ValueError("patterns must contain at least one non-empty trace pattern.")
    instruction = " ".join((".save", *normalized_patterns))
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="save",
        schematic_warning=(
            "Prepared a schematic artifact with one `.save` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.save` directive.",
        output_path=output_path,
    )
    return PreparedSaveDirective(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(
            warning,
            "`.save` limits stored waveform traces (wildcards `*` and `?` supported); "
            "it is ignored for `.noise` simulations.",
        ),
    )


__all__ = ["SERVICE_SPEC", "PreparedSaveDirective", "prepare_save"]
