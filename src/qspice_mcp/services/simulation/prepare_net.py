"""Service for staging a source with a documented `.net` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreparedNetworkAnalysis:
    """Metadata for one source staged with a `.net` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_net",
    title="Prepare Network Parameter Analysis",
    summary=(
        "Stage a schematic or netlist with a documented `.net` directive for "
        "S/Y/Z/H one- or two-port parameter extraction alongside `.ac`."
    ),
    phase="implemented",
    read_only=False,
)


def prepare_net(
    source_path: str | Path,
    *,
    workspace_root: Path,
    input_source: str,
    output_resistor: str | None = None,
    output_path: str | Path | None = None,
) -> PreparedNetworkAnalysis:
    """Stage a source with one documented `.net` directive."""

    normalized_input = input_source.strip()
    if not normalized_input:
        raise ValueError("input_source must not be blank.")
    tokens = [".net"]
    if output_resistor is not None:
        normalized_resistor = output_resistor.strip()
        if not normalized_resistor:
            raise ValueError("output_resistor must not be blank when provided.")
        tokens.append(normalized_resistor)
    tokens.append(normalized_input)
    instruction = " ".join(tokens)

    port_note = (
        "Two-port S/Y/Z/H parameters will be computed (input source plus output resistor)."
        if output_resistor is not None
        else "One-port parameters (S11, Zin, Yin) will be computed; Smith chart plotting "
        "of S11 is supported when extraction succeeds."
    )
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="net",
        schematic_warning=(
            "Prepared a schematic artifact with one `.net` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.net` directive.",
        output_path=output_path,
    )
    return PreparedNetworkAnalysis(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(
            warning,
            "`.net` only produces results together with an `.ac` analysis directive; "
            "stage one with `prepare_ac` if not already present.",
            f"The input source must declare its source impedance via `Rser`. {port_note}",
        ),
    )


__all__ = ["SERVICE_SPEC", "PreparedNetworkAnalysis", "prepare_net"]
