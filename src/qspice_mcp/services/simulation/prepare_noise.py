"""Service for staging a source with a documented `.noise` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_NOISE_SWEEP_TYPES = frozenset({"dec", "oct", "lin", "list"})


@dataclass(frozen=True, slots=True)
class PreparedNoiseAnalysis:
    """Metadata for one source staged with a `.noise` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_noise",
    title="Prepare Noise Analysis",
    summary="Stage a schematic or netlist with a documented `.noise` directive.",
    phase="implemented",
    read_only=False,
)


def prepare_noise(
    source_path: str | Path,
    *,
    workspace_root: Path,
    output_node: str,
    input_source: str,
    sweep_type: str,
    points: str | None = None,
    start: str | None = None,
    stop: str | None = None,
    frequencies: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> PreparedNoiseAnalysis:
    """Stage a source with one documented `.noise` directive."""

    normalized_sweep_type = sweep_type.strip().lower()
    if normalized_sweep_type not in _NOISE_SWEEP_TYPES:
        allowed = ", ".join(sorted(_NOISE_SWEEP_TYPES))
        raise ValueError(f"sweep_type must be one of: {allowed}")
    if normalized_sweep_type == "list":
        values = tuple(value.strip() for value in (frequencies or ()) if value.strip())
        if not values:
            raise ValueError("List sweep requires at least one value in frequencies.")
        instruction = " ".join(
            (".noise", output_node.strip(), input_source.strip(), "list", *values)
        )
    else:
        if points is None or start is None or stop is None:
            raise ValueError(f"`{normalized_sweep_type}` sweep requires points, start, and stop.")
        instruction = " ".join(
            (
                ".noise",
                output_node.strip(),
                input_source.strip(),
                normalized_sweep_type,
                points.strip(),
                start.strip(),
                stop.strip(),
            )
        )
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="noise",
        schematic_warning=(
            "Prepared a schematic artifact with one `.noise` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.noise` directive.",
        output_path=output_path,
    )
    return PreparedNoiseAnalysis(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "PreparedNoiseAnalysis", "prepare_noise"]
