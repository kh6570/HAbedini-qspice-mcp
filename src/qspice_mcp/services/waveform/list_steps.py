"""Service for enumerating simulation steps for a raw artifact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.waveform import get_step_indices, open_raw_reader
from qspice_mcp.services._internals.step_filters import StepFilterValue, build_step_value_maps
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_log import LogStepVariable, read_log

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class StepSummary:
    """One resolved simulation step and its variable assignments."""

    index: int
    values: dict[str, StepFilterValue]


@dataclass(frozen=True, slots=True)
class StepCatalog:
    """Step inventory for one raw/log artifact pair."""

    raw_path: Path
    log_path: Path | None
    step_count: int
    step_variables: tuple[LogStepVariable, ...]
    steps: tuple[StepSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="list_steps",
    title="List Steps",
    summary="Enumerate available simulation steps and their variable assignments.",
    phase="implemented",
)


def list_steps(raw_path: str | Path, *, workspace_root: Path) -> StepCatalog:
    """Enumerate the available steps for one `.qraw` file."""

    normalized_workspace = workspace_root.resolve(strict=False)
    reader, resolved_path = open_raw_reader(raw_path, workspace_root=normalized_workspace)
    step_indices = get_step_indices(reader)
    resolved_log_path = resolved_path.with_suffix(".log").resolve(strict=False)

    warnings: list[str] = []
    step_variables: tuple[LogStepVariable, ...] = ()
    if resolved_log_path.is_file():
        inspection = read_log(
            resolved_log_path,
            workspace_root=normalized_workspace,
            include_measures=False,
            max_lines=0,
        )
        step_variables = inspection.step_variables
        if inspection.step_count not in {0, len(step_indices)}:
            warnings.append(
                "Log-reported step count differed from raw-reported step count; "
                "using the raw artifact as the source of truth."
            )
    else:
        warnings.append(
            "No sibling .log file was found, so step variable names could not be recovered."
        )

    rendered_values = build_step_value_maps(step_variables, len(step_indices))
    steps = tuple(
        StepSummary(
            index=int(step_index),
            values=rendered_values[position] if position < len(rendered_values) else {},
        )
        for position, step_index in enumerate(step_indices)
    )

    return StepCatalog(
        raw_path=resolved_path,
        log_path=resolved_log_path if resolved_log_path.is_file() else None,
        step_count=len(step_indices),
        step_variables=step_variables,
        steps=steps,
        warnings=tuple(warnings),
    )


__all__ = ["SERVICE_SPEC", "StepCatalog", "StepSummary", "list_steps"]
