"""Service for staging a source with a documented `.options` directive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path

_INTEGRATION_METHODS = frozenset({"trap", "gear"})


@dataclass(frozen=True, slots=True)
class PreparedSimulatorOptions:
    """Metadata for one source staged with a `.options` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_options",
    title="Prepare Simulator Options",
    summary=(
        "Stage a schematic or netlist with a documented `.options` directive "
        "covering convergence, Bode/FRA, and output bookkeeping options."
    ),
    phase="implemented",
    read_only=False,
)


def _append_value_option(tokens: list[str], name: str, value: str | None) -> None:
    if value is None:
        return
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"Option {name!r} must not be blank when provided.")
    tokens.append(f"{name}={stripped}")


def _append_flag_option(tokens: list[str], name: str, enabled: bool | None) -> None:
    if enabled:
        tokens.append(f"{name}=1")


def prepare_options(
    source_path: str | Path,
    *,
    workspace_root: Path,
    cshunt: str | None = None,
    gshunt: str | None = None,
    gmin: str | None = None,
    gminsteps: str | None = None,
    srcsteps: str | None = None,
    noopiter: bool | None = None,
    feather: str | None = None,
    reltol: str | None = None,
    abstol: str | None = None,
    vntol: str | None = None,
    method: str | None = None,
    itl1: str | None = None,
    itl4: str | None = None,
    maxstep: str | None = None,
    max1ststep: str | None = None,
    ric: str | None = None,
    boderef: str | None = None,
    bodeampfreq: str | None = None,
    bodelopow: str | None = None,
    bodehipow: str | None = None,
    savepowers: bool | None = None,
    keepopinfo: bool | None = None,
    fastmath2: bool | None = None,
    output_path: str | Path | None = None,
) -> PreparedSimulatorOptions:
    """Stage a source with one documented `.options` directive."""

    normalized_method: str | None = None
    if method is not None:
        normalized_method = method.strip().lower()
        if normalized_method not in _INTEGRATION_METHODS:
            allowed = ", ".join(sorted(_INTEGRATION_METHODS))
            raise ValueError(f"method must be one of: {allowed}")

    tokens: list[str] = []
    _append_value_option(tokens, "cshunt", cshunt)
    _append_value_option(tokens, "gshunt", gshunt)
    _append_value_option(tokens, "gmin", gmin)
    _append_value_option(tokens, "gminsteps", gminsteps)
    _append_value_option(tokens, "srcsteps", srcsteps)
    _append_flag_option(tokens, "noopiter", noopiter)
    _append_value_option(tokens, "feather", feather)
    _append_value_option(tokens, "reltol", reltol)
    _append_value_option(tokens, "abstol", abstol)
    _append_value_option(tokens, "vntol", vntol)
    _append_value_option(tokens, "method", normalized_method)
    _append_value_option(tokens, "itl1", itl1)
    _append_value_option(tokens, "itl4", itl4)
    _append_value_option(tokens, "maxstep", maxstep)
    _append_value_option(tokens, "max1ststep", max1ststep)
    _append_value_option(tokens, "ric", ric)
    _append_value_option(tokens, "boderef", boderef)
    _append_value_option(tokens, "bodeampfreq", bodeampfreq)
    _append_value_option(tokens, "bodelopow", bodelopow)
    _append_value_option(tokens, "bodehipow", bodehipow)
    _append_flag_option(tokens, "savepowers", savepowers)
    _append_flag_option(tokens, "keepopinfo", keepopinfo)
    _append_flag_option(tokens, "fastmath2", fastmath2)
    if not tokens:
        raise ValueError("At least one simulator option must be provided.")

    instruction = " ".join((".options", *tokens))
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=instruction,
        default_stem_suffix="options",
        schematic_warning=(
            "Prepared a schematic artifact with one `.options` directive. "
            "Run simulation on the staged output."
        ),
        netlist_warning="Prepared a netlist copy with one `.options` directive.",
        output_path=output_path,
    )
    return PreparedSimulatorOptions(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        instruction=instruction,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "PreparedSimulatorOptions", "prepare_options"]
