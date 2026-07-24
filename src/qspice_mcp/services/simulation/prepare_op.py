"""Service for staging a source with a documented `.op` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreparedOperatingPointAnalysis:
    """Metadata for one source staged with a `.op` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_op",
    title="Prepare Operating Point Analysis",
    summary="Stage a schematic or netlist with a documented `.op` bias-point directive.",
    phase="implemented",
    read_only=False,
)


def prepare_op(
    source_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
) -> PreparedOperatingPointAnalysis:
    """Stage a source with one documented `.op` directive."""

    instruction = ".op"
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="op",
        schematic_warning=(
            "Prepared a schematic artifact with one `.op` directive. "
            "Run simulation on the staged output, then inspect results with "
            "`read_device_operating_points`."
        ),
        netlist_warning=(
            "Prepared a netlist copy with one `.op` directive. "
            "Run simulation on the staged output, then inspect results with "
            "`read_device_operating_points`."
        ),
        output_path=output_path,
    )
    return PreparedOperatingPointAnalysis(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "PreparedOperatingPointAnalysis", "prepare_op"]
