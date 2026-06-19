"""Service for staging a source with a documented `.sens` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path

_SENS_ANALYSIS_TYPES = frozenset({"dc", "ac"})


@dataclass(frozen=True, slots=True)
class PreparedSensitivityAnalysis:
    """Metadata for one source staged with a `.sens` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_sensitivity",
    title="Prepare Sensitivity Analysis",
    summary="Stage a schematic or netlist with a documented `.sens` directive.",
    phase="implemented",
    read_only=False,
)


def prepare_sensitivity(
    source_path: str | Path,
    *,
    workspace_root: Path,
    analysis_type: str,
    output_node: str,
    output_path: str | Path | None = None,
) -> PreparedSensitivityAnalysis:
    """Stage a source with one documented `.sens` directive."""

    normalized_analysis_type = analysis_type.strip().lower()
    if normalized_analysis_type not in _SENS_ANALYSIS_TYPES:
        allowed = ", ".join(sorted(_SENS_ANALYSIS_TYPES))
        raise ValueError(f"analysis_type must be one of: {allowed}")
    instruction = " ".join(
        (".sens", normalized_analysis_type, output_node.strip()),
    )
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="sens",
        schematic_warning=(
            "Prepared a schematic artifact with one `.sens` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.sens` directive.",
        output_path=output_path,
    )
    return PreparedSensitivityAnalysis(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "PreparedSensitivityAnalysis", "prepare_sensitivity"]
