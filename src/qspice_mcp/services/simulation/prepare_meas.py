"""Service for staging a source with a documented `.meas` statement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import stage_analysis_directive

if TYPE_CHECKING:
    from pathlib import Path

MeasKind = Literal["find_at", "avg", "trig_targ", "fra", "four", "raw"]

_MEAS_KINDS = frozenset({"find_at", "avg", "trig_targ", "fra", "four", "raw"})
_AVG_STATISTICS = frozenset({"avg", "max", "min", "pp", "rms", "integ"})


@dataclass(frozen=True, slots=True)
class PreparedMeasStatement:
    """Metadata for one source staged with a `.meas` statement."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    kind: MeasKind
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_meas",
    title="Prepare Measure Statement",
    summary=(
        "Stage a schematic or netlist with a documented `.meas` statement, "
        "including `.meas fra` frequency-response verification points."
    ),
    phase="implemented",
    read_only=False,
)


def _require(value: str | None, *, field: str, kind: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field} is required for kind={kind!r}.")
    return value.strip()


def _validate_name(name: str | None, *, kind: str) -> str:
    normalized = _require(name, field="name", kind=kind)
    if any(character.isspace() for character in normalized):
        raise ValueError("name must not contain whitespace.")
    return normalized


def _render_meas_instruction(
    kind: MeasKind,
    *,
    name: str | None,
    expression: str | None,
    at: str | None,
    statistic: str | None,
    start: str | None,
    stop: str | None,
    trig: str | None,
    targ: str | None,
    frequency: str | None,
    input_expression: str | None,
    output_expression: str | None,
    instruction: str | None,
) -> str:
    if kind == "raw":
        normalized = _require(instruction, field="instruction", kind=kind)
        if not normalized.lower().startswith(".meas"):
            raise ValueError("Raw instruction must start with `.meas`.")
        return normalized

    measure_name = _validate_name(name, kind=kind)
    if kind == "find_at":
        rendered_expression = _require(expression, field="expression", kind=kind)
        rendered_at = _require(at, field="at", kind=kind)
        return f".meas {measure_name} find {rendered_expression} at {rendered_at}"
    if kind == "avg":
        rendered_statistic = (statistic or "avg").strip().lower()
        if rendered_statistic not in _AVG_STATISTICS:
            allowed = ", ".join(sorted(_AVG_STATISTICS))
            raise ValueError(f"statistic must be one of: {allowed}")
        rendered_expression = _require(expression, field="expression", kind=kind)
        tokens = [".meas", measure_name, rendered_statistic, rendered_expression]
        if (start is None) != (stop is None):
            raise ValueError("start and stop must be provided together for kind='avg'.")
        if start is not None and stop is not None:
            tokens.extend(("from", start.strip(), "to", stop.strip()))
        return " ".join(tokens)
    if kind == "trig_targ":
        rendered_trig = _require(trig, field="trig", kind=kind)
        rendered_targ = _require(targ, field="targ", kind=kind)
        if "=" not in rendered_trig or "=" not in rendered_targ:
            raise ValueError(
                "trig and targ must be EXPRESSION=EXPRESSION conditions (for example V(out)=2.5)."
            )
        return f".meas {measure_name} trig {rendered_trig} targ {rendered_targ}"
    if kind == "fra":
        rendered_frequency = _require(frequency, field="frequency", kind=kind)
        rendered_input = _require(input_expression, field="input_expression", kind=kind)
        rendered_output = _require(output_expression, field="output_expression", kind=kind)
        return f".meas {measure_name} fra {rendered_frequency} {rendered_input} {rendered_output}"
    # The remaining kind is Fourier analysis.
    rendered_frequency = _require(frequency, field="frequency", kind=kind)
    rendered_expression = _require(expression, field="expression", kind=kind)
    return f".meas {measure_name} four {rendered_frequency} {rendered_expression}"


def prepare_meas(
    source_path: str | Path,
    *,
    workspace_root: Path,
    kind: str,
    name: str | None = None,
    expression: str | None = None,
    at: str | None = None,
    statistic: str | None = None,
    start: str | None = None,
    stop: str | None = None,
    trig: str | None = None,
    targ: str | None = None,
    frequency: str | None = None,
    input_expression: str | None = None,
    output_expression: str | None = None,
    instruction: str | None = None,
    output_path: str | Path | None = None,
) -> PreparedMeasStatement:
    """Stage a source with one documented `.meas` statement.

    Results are computed post-simulation by QPOST and readable through
    `read_measures`; `.meas fra` is the most reliable way to verify individual
    `.bode` frequency-response points.
    """

    normalized_kind = kind.strip().lower()
    if normalized_kind not in _MEAS_KINDS:
        allowed = ", ".join(sorted(_MEAS_KINDS))
        raise ValueError(f"kind must be one of: {allowed}")
    meas_kind = cast("MeasKind", normalized_kind)

    rendered = _render_meas_instruction(
        meas_kind,
        name=name,
        expression=expression,
        at=at,
        statistic=statistic,
        start=start,
        stop=stop,
        trig=trig,
        targ=targ,
        frequency=frequency,
        input_expression=input_expression,
        output_expression=output_expression,
        instruction=instruction,
    )
    source, destination, source_kind, warning = stage_analysis_directive(
        source_path,
        workspace_root=workspace_root,
        instruction=rendered,
        default_stem_suffix="meas",
        schematic_warning=(
            "Prepared a schematic artifact with one `.meas` statement. "
            "Run simulation on the staged output, then use `read_measures`."
        ),
        netlist_warning=(
            "Prepared a netlist copy with one `.meas` statement. "
            "Run simulation on the staged output, then use `read_measures`."
        ),
        output_path=output_path,
    )
    return PreparedMeasStatement(
        source_path=source,
        output_path=destination,
        source_kind=source_kind,
        kind=meas_kind,
        instruction=rendered,
        warnings=(warning,),
    )


__all__ = ["SERVICE_SPEC", "MeasKind", "PreparedMeasStatement", "prepare_meas"]
