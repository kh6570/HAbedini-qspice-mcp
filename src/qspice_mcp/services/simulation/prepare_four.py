"""Service for staging a source with a documented `.four` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class PreparedFourierAnalysis:
    """Metadata for one source staged with a `.four` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_four",
    title="Prepare Fourier Analysis",
    summary=(
        "Stage a schematic or netlist with a documented `.four` THD directive "
        "whose results are parsed post-simulation by `read_fourier`."
    ),
    phase="implemented",
    read_only=False,
)


def prepare_four(
    source_path: str | Path,
    *,
    workspace_root: Path,
    frequency: str,
    expressions: Sequence[str],
    harmonics: int | None = None,
    periods: int | None = None,
    output_path: str | Path | None = None,
) -> PreparedFourierAnalysis:
    """Stage a source with one documented `.four` directive."""

    normalized_frequency = frequency.strip()
    if not normalized_frequency:
        raise ValueError("frequency must not be blank.")
    normalized_expressions = tuple(
        expression.strip() for expression in expressions if expression.strip()
    )
    if not normalized_expressions:
        raise ValueError("expressions must contain at least one non-empty expression.")
    if periods is not None and harmonics is None:
        raise ValueError(
            "harmonics must be provided when periods is set "
            "(`.four FREQ [HARMONICS] [PERIODS]` arguments are positional)."
        )
    if harmonics is not None and harmonics < 1:
        raise ValueError("harmonics must be at least 1.")
    if periods is not None and periods < 1:
        raise ValueError("periods must be at least 1.")

    tokens = [".four", normalized_frequency]
    if harmonics is not None:
        tokens.append(str(harmonics))
    if periods is not None:
        tokens.append(str(periods))
    tokens.extend(normalized_expressions)
    instruction = " ".join(tokens)

    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="four",
        schematic_warning=(
            "Prepared a schematic artifact with one `.four` directive. "
            "Run simulation on the staged output, then parse results with `read_fourier`."
        ),
        netlist_warning=(
            "Prepared a netlist copy with one `.four` directive. "
            "Run simulation on the staged output, then parse results with `read_fourier`."
        ),
        output_path=output_path,
    )
    return PreparedFourierAnalysis(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(
            warning,
            "`.four` uses the last PERIODS/FREQ seconds of transient data; ensure the "
            "`.tran` runs long enough and the circuit has a single sine source for a "
            "meaningful THD.",
        ),
    )


__all__ = ["SERVICE_SPEC", "PreparedFourierAnalysis", "prepare_four"]
