"""Service for enumerating QPOST-derived measurement blocks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_log import read_log

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class MeasureSummary:
    """Metadata for one measurement block."""

    name: str
    analysis: str
    expression: str
    value_columns: tuple[str, ...]
    row_count: int
    stepped: bool


@dataclass(frozen=True, slots=True)
class MeasureCatalog:
    """Measurement inventory for one simulation log."""

    log_path: Path
    meas_path: Path | None
    step_count: int
    measure_count: int
    measures: tuple[MeasureSummary, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="list_measures",
    title="List Measures",
    summary="Enumerate the QPOST-derived measurement blocks available for one simulation log.",
    phase="implemented",
)


def list_measures(
    log_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None = None,
    refresh_measures: bool = True,
    meas_path: str | Path | None = None,
    timeout_s: float | None = None,
) -> MeasureCatalog:
    """Enumerate measurement blocks available for one `.log` file."""

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
    measures = tuple(
        MeasureSummary(
            name=measure.name,
            analysis=measure.analysis,
            expression=measure.expression,
            value_columns=measure.columns[1:]
            if measure.columns[:1] == ("step",)
            else measure.columns,
            row_count=len(measure.rows),
            stepped=measure.columns[:1] == ("step",),
        )
        for measure in inspection.measures
    )
    return MeasureCatalog(
        log_path=inspection.log_path,
        meas_path=inspection.meas_path,
        step_count=inspection.step_count,
        measure_count=len(measures),
        measures=measures,
        warnings=inspection.warnings,
    )


__all__ = ["SERVICE_SPEC", "MeasureCatalog", "MeasureSummary", "list_measures"]
