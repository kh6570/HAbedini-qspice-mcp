"""Service for staging a source with a documented temperature `.step` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreparedTemperatureSweep:
    """Metadata for one source staged with a temperature sweep directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_temperature_sweep",
    title="Prepare Temperature Sweep",
    summary="Stage a schematic or netlist with a documented `.step temp` directive.",
    phase="implemented",
    read_only=False,
)


def prepare_temperature_sweep(
    source_path: str | Path,
    *,
    workspace_root: Path,
    start: str,
    stop: str,
    step: str,
    output_path: str | Path | None = None,
) -> PreparedTemperatureSweep:
    """Stage a source with one documented `.step temp` sweep directive."""

    instruction = " ".join((".step", "temp", start.strip(), stop.strip(), step.strip()))
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="temp",
        schematic_warning=(
            "Prepared a schematic artifact with one `.step temp` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.step temp` directive.",
        output_path=output_path,
    )
    return PreparedTemperatureSweep(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "PreparedTemperatureSweep", "prepare_temperature_sweep"]
