"""Service for reading QPOST-derived measurement values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._internals.step_filters import StepFilterValue, resolve_step_selection
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_log import LogMeasurement, LogStepVariable, read_log

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class MeasureRow:
    """One measurement row, optionally tied to a simulation step."""

    step: int | None
    values: dict[str, StepFilterValue]


@dataclass(frozen=True, slots=True)
class MeasureResult:
    """One requested measurement block and its selected rows."""

    name: str
    analysis: str
    expression: str
    value_columns: tuple[str, ...]
    rows: tuple[MeasureRow, ...]


@dataclass(frozen=True, slots=True)
class MeasureRead:
    """Measurement values resolved from one simulation log."""

    log_path: Path
    meas_path: Path | None
    step_count: int
    resolved_step: int | None
    measures: tuple[MeasureResult, ...]
    warnings: tuple[str, ...] = ()
    measure_rows_truncated: bool = False


SERVICE_SPEC = ServiceSpec(
    name="read_measures",
    title="Read Measures",
    summary="Return QPOST-derived measurement values with optional step filtering.",
    phase="implemented",
    # Not read-only: refresh_measures (default) materializes a `.meas` sidecar via QPOST.
    read_only=False,
)


def _is_stepped_measure(measure: LogMeasurement) -> bool:
    """Return whether one parsed measurement block carries a step column."""

    return measure.columns[:1] == ("step",)


def _row_step_index(row: tuple[StepFilterValue, ...]) -> int | None:
    """Convert a one-based `.meas` step ordinal to a zero-based step index."""

    if not row:
        return None
    first_value = row[0]
    if not isinstance(first_value, (int, float)):
        return None
    return int(first_value) - 1


def _row_to_measure_row(measure: LogMeasurement, row: tuple[StepFilterValue, ...]) -> MeasureRow:
    """Convert one parsed row into a user-facing measurement row."""

    stepped = _is_stepped_measure(measure)
    if stepped:
        value_columns = measure.columns[1:]
        values = {
            column: row[index + 1]
            for index, column in enumerate(value_columns)
            if index + 1 < len(row)
        }
        return MeasureRow(step=_row_step_index(row), values=values)

    values = {
        column: row[index] for index, column in enumerate(measure.columns) if index < len(row)
    }
    return MeasureRow(step=None, values=values)


def _resolve_requested_step(
    step_count: int,
    *,
    step: int | None,
    step_filters: Mapping[str, object] | None,
    step_variables: Sequence[LogStepVariable],
) -> int | None:
    """Resolve an optional step request for measurement reads."""

    if step_filters:
        effective_step_count = step_count if step_count > 0 else 1
        return resolve_step_selection(
            step_variables,
            effective_step_count,
            step=step,
            step_filters=step_filters,
            default_step=0,
        )
    if step is None:
        return None
    if step_count == 0:
        if step != 0:
            raise ValueError("This measurement set is not stepped; only step index 0 is valid.")
        return 0
    return resolve_step_selection(step_variables, step_count, step=step, default_step=0)


def _select_measures(
    measures: tuple[LogMeasurement, ...],
    requested_names: Sequence[str] | None,
) -> tuple[LogMeasurement, ...]:
    """Select a subset of measures by name, case-insensitively."""

    if not requested_names:
        return measures

    by_name = {measure.name.lower(): measure for measure in measures}
    selected: list[LogMeasurement] = []
    missing: list[str] = []
    for name in requested_names:
        match = by_name.get(name.lower())
        if match is None:
            missing.append(name)
            continue
        selected.append(match)
    if missing:
        available = ", ".join(sorted(by_name))
        raise ValueError(
            f"Requested measure(s) were not found: {', '.join(missing)}. "
            f"Available measures: {available}"
        )
    return tuple(selected)


def read_measures(
    log_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None = None,
    measures: tuple[str, ...] | list[str] | None = None,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    refresh_measures: bool = True,
    meas_path: str | Path | None = None,
    timeout_s: float | None = None,
    max_measure_rows: int | None = None,
) -> MeasureRead:
    """Return requested measurement values from one `.log` file.

    ``max_measure_rows`` bounds the rows returned per measurement block after
    step filtering; ``measure_rows_truncated`` flags cuts.
    """

    if max_measure_rows is not None and max_measure_rows < 1:
        raise ValidationError("max_measure_rows must be a positive integer.")
    resolved_workspace_root = workspace_root.resolve(strict=False)
    if timeout_s is None:
        inspection = read_log(
            log_path,
            workspace_root=resolved_workspace_root,
            settings=settings,
            max_lines=0,
            include_measures=True,
            refresh_measures=refresh_measures,
            meas_path=meas_path,
        )
    else:
        inspection = read_log(
            log_path,
            workspace_root=resolved_workspace_root,
            settings=settings,
            max_lines=0,
            include_measures=True,
            refresh_measures=refresh_measures,
            meas_path=meas_path,
            timeout_s=timeout_s,
        )
    selected_measures = _select_measures(inspection.measures, measures)
    resolved_step = _resolve_requested_step(
        inspection.step_count,
        step=step,
        step_filters=step_filters,
        step_variables=inspection.step_variables,
    )

    rendered_measures: list[MeasureResult] = []
    measure_rows_truncated = False
    for measure in selected_measures:
        rows = tuple(_row_to_measure_row(measure, row) for row in measure.rows)
        if resolved_step is not None:
            if _is_stepped_measure(measure):
                rows = tuple(row for row in rows if row.step == resolved_step)
            elif resolved_step != 0:
                raise ValueError(
                    "Requested step selection is not available because the "
                    "selected measure is not stepped."
                )
        if max_measure_rows is not None and len(rows) > max_measure_rows:
            rows = rows[:max_measure_rows]
            measure_rows_truncated = True
        rendered_measures.append(
            MeasureResult(
                name=measure.name,
                analysis=measure.analysis,
                expression=measure.expression,
                value_columns=measure.columns[1:]
                if _is_stepped_measure(measure)
                else measure.columns,
                rows=rows,
            )
        )

    return MeasureRead(
        log_path=inspection.log_path,
        meas_path=inspection.meas_path,
        step_count=inspection.step_count,
        resolved_step=resolved_step,
        measures=tuple(rendered_measures),
        warnings=inspection.warnings,
        measure_rows_truncated=measure_rows_truncated,
    )


__all__ = [
    "SERVICE_SPEC",
    "MeasureRead",
    "MeasureResult",
    "MeasureRow",
    "read_measures",
]
