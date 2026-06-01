"""Service for summarizing tolerance-analysis result measures and target coverage."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, stdev
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import (
    batch_run_record_path,
    load_batch_manifest,
    load_batch_run_record,
)
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation.prepare_monte_carlo import load_prepared_monte_carlo
from qspice_mcp.services.simulation.prepare_worst_case import load_prepared_worst_case
from qspice_mcp.services.waveform.read_measures import read_measures

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings
    from qspice_mcp.services._internals.simulation_batch import SimulationBatchRun
    from qspice_mcp.services.simulation.prepare_monte_carlo import (
        MonteCarloComponentValue,
        MonteCarloParameter,
        MonteCarloSample,
    )
    from qspice_mcp.services.simulation.prepare_worst_case import (
        WorstCaseCase,
        WorstCaseComponentValue,
        WorstCaseParameter,
    )

    PreparedAssignment = MonteCarloSample | WorstCaseCase
    PreparedParameterTarget = MonteCarloParameter | WorstCaseParameter
    PreparedComponentTarget = MonteCarloComponentValue | WorstCaseComponentValue


@dataclass(frozen=True, slots=True)
class _PreparedTolerancePlan:
    plan_path: Path
    seed: int | None
    parameter_targets: Sequence[PreparedParameterTarget]
    component_targets: Sequence[PreparedComponentTarget]
    samples: Sequence[PreparedAssignment]


@dataclass(frozen=True, slots=True)
class ToleranceParameterSummary:
    """Summary statistics for one varied tolerance-analysis parameter."""

    name: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    sample_count: int
    sampled_min: float
    sampled_max: float
    mean: float
    stdev: float
    completed_sample_count: int = 0
    completed_sampled_min: float | None = None
    completed_sampled_max: float | None = None
    completed_mean: float | None = None
    completed_stdev: float | None = None


@dataclass(frozen=True, slots=True)
class ToleranceComponentValueSummary:
    """Summary statistics for one varied component reference."""

    reference: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    sample_count: int
    sampled_min: float
    sampled_max: float
    mean: float
    stdev: float
    completed_sample_count: int = 0
    completed_sampled_min: float | None = None
    completed_sampled_max: float | None = None
    completed_mean: float | None = None
    completed_stdev: float | None = None


@dataclass(frozen=True, slots=True)
class ToleranceMeasureSummary:
    """Summary statistics for one aggregated measurement column."""

    name: str
    analysis: str
    expression: str
    column: str
    sample_count: int
    minimum: float
    maximum: float
    mean: float
    stdev: float


@dataclass(frozen=True, slots=True)
class ToleranceAnalysisSummary:
    """Combined target and measure summary for one tolerance-analysis batch."""

    batch_path: Path
    plan_path: Path
    source_path: Path
    output_root: Path
    sweep_kind: str
    seed: int | None
    status: str
    run_count: int
    completed_run_count: int
    successful_run_count: int
    failed_run_count: int
    parameter_summaries: tuple[ToleranceParameterSummary, ...]
    measure_summaries: tuple[ToleranceMeasureSummary, ...]
    component_value_summaries: tuple[ToleranceComponentValueSummary, ...] = ()
    pending_run_count: int = 0
    completion_pct: float = 0.0
    measure_coverage_run_count: int = 0
    missing_measure_run_count: int = 0
    measure_coverage_pct: float = 0.0
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="summarize_tolerance_analysis",
    title="Summarize Tolerance Analysis",
    summary="Summarize Monte Carlo or worst-case target coverage and numeric `.meas` results.",
    phase="implemented",
)


def _summarize_values(values: list[float]) -> tuple[int, float, float, float, float]:
    count = len(values)
    mean = fmean(values)
    return count, min(values), max(values), mean, stdev(values) if count > 1 else 0.0


def _summarize_optional_values(
    values: list[float],
) -> tuple[int, float, float, float, float] | None:
    if not values:
        return None
    return _summarize_values(values)


def _load_prepared_tolerance_plan(
    *, batch_plan_path: Path, sweep_kind: str, workspace_root: Path
) -> _PreparedTolerancePlan:
    if sweep_kind == "monte_carlo":
        monte_carlo_plan = load_prepared_monte_carlo(batch_plan_path, workspace_root=workspace_root)
        return _PreparedTolerancePlan(
            plan_path=monte_carlo_plan.plan_path,
            seed=monte_carlo_plan.seed,
            parameter_targets=monte_carlo_plan.parameters,
            component_targets=monte_carlo_plan.component_values,
            samples=monte_carlo_plan.samples,
        )

    worst_case_plan = load_prepared_worst_case(batch_plan_path, workspace_root=workspace_root)
    return _PreparedTolerancePlan(
        plan_path=worst_case_plan.plan_path,
        seed=None,
        parameter_targets=worst_case_plan.parameters,
        component_targets=worst_case_plan.component_values,
        samples=worst_case_plan.cases,
    )


def _build_parameter_summaries(
    parameter_targets: Sequence[PreparedParameterTarget],
    samples: Sequence[PreparedAssignment],
    completed_samples: Sequence[PreparedAssignment],
) -> tuple[ToleranceParameterSummary, ...]:
    summaries: list[ToleranceParameterSummary] = []
    for parameter in parameter_targets:
        values = [float(sample.parameter_values[parameter.name]) for sample in samples]
        count, sampled_min, sampled_max, mean, sample_stdev = _summarize_values(values)
        completed_values = [
            float(sample.parameter_values[parameter.name]) for sample in completed_samples
        ]
        completed_summary = _summarize_optional_values(completed_values)
        summaries.append(
            ToleranceParameterSummary(
                name=parameter.name,
                nominal=parameter.nominal,
                tolerance_pct=parameter.tolerance_pct,
                minimum=parameter.minimum,
                maximum=parameter.maximum,
                sample_count=count,
                sampled_min=sampled_min,
                sampled_max=sampled_max,
                mean=mean,
                stdev=sample_stdev,
                completed_sample_count=0 if completed_summary is None else completed_summary[0],
                completed_sampled_min=None if completed_summary is None else completed_summary[1],
                completed_sampled_max=None if completed_summary is None else completed_summary[2],
                completed_mean=None if completed_summary is None else completed_summary[3],
                completed_stdev=None if completed_summary is None else completed_summary[4],
            )
        )
    return tuple(summaries)


def _build_component_value_summaries(
    component_targets: Sequence[PreparedComponentTarget],
    samples: Sequence[PreparedAssignment],
    completed_samples: Sequence[PreparedAssignment],
) -> tuple[ToleranceComponentValueSummary, ...]:
    summaries: list[ToleranceComponentValueSummary] = []
    for component in component_targets:
        values = [float(sample.component_values[component.reference]) for sample in samples]
        count, sampled_min, sampled_max, mean, sample_stdev = _summarize_values(values)
        completed_values = [
            float(sample.component_values[component.reference]) for sample in completed_samples
        ]
        completed_summary = _summarize_optional_values(completed_values)
        summaries.append(
            ToleranceComponentValueSummary(
                reference=component.reference,
                nominal=component.nominal,
                tolerance_pct=component.tolerance_pct,
                minimum=component.minimum,
                maximum=component.maximum,
                sample_count=count,
                sampled_min=sampled_min,
                sampled_max=sampled_max,
                mean=mean,
                stdev=sample_stdev,
                completed_sample_count=0 if completed_summary is None else completed_summary[0],
                completed_sampled_min=None if completed_summary is None else completed_summary[1],
                completed_sampled_max=None if completed_summary is None else completed_summary[2],
                completed_mean=None if completed_summary is None else completed_summary[3],
                completed_stdev=None if completed_summary is None else completed_summary[4],
            )
        )
    return tuple(summaries)


def _merge_runs_with_sidecars(
    *,
    source_path: Path,
    output_root: Path,
    workspace_root: Path,
    samples: Sequence[PreparedAssignment],
    manifest_runs: Sequence[SimulationBatchRun],
) -> tuple[tuple[SimulationBatchRun, ...], tuple[str, ...]]:
    runs_by_index = {run.index: run for run in manifest_runs}
    recovered_count = 0

    for sample in samples:
        if sample.index in runs_by_index:
            continue
        label = sample.label or f"sample-{sample.index:03d}"
        record_path = batch_run_record_path(
            source_path,
            output_root=output_root,
            index=sample.index,
            label=label,
        )
        if not record_path.is_file():
            continue
        recovered = load_batch_run_record(record_path, workspace_root=workspace_root)
        if recovered.label != label:
            continue
        runs_by_index[sample.index] = recovered
        recovered_count += 1

    warnings: tuple[str, ...] = ()
    if recovered_count:
        warnings = (
            f"Recovered {recovered_count} completed run(s) from per-run sidecars that were newer "
            "than the batch manifest.",
        )
    return tuple(sorted(runs_by_index.values(), key=lambda run: run.index)), warnings


def _collect_measure_values(
    *,
    successful_runs: Sequence[SimulationBatchRun],
    workspace_root: Path,
    settings: QSpiceSettings | None,
    measures: tuple[str, ...] | list[str] | None,
    refresh_measures: bool,
    warnings: list[str],
) -> tuple[dict[tuple[str, str, str, str], list[float]], frozenset[int]]:
    measure_values: dict[tuple[str, str, str, str], list[float]] = {}
    measured_run_indexes: set[int] = set()
    for run in successful_runs:
        run_contributed = False
        try:
            measured = read_measures(
                run.log_path,
                workspace_root=workspace_root,
                settings=settings,
                measures=measures,
                refresh_measures=refresh_measures,
            )
        except Exception as exc:
            warnings.append(f"Run {run.index} ({run.label}) measures were skipped: {exc}")
            continue

        for measure in measured.measures:
            if len(measure.rows) != 1:
                warnings.append(
                    f"Run {run.index} ({run.label}) measure {measure.name!r} was skipped "
                    "because it did not yield exactly one row."
                )
                continue
            row = measure.rows[0]
            for column in measure.value_columns:
                value = row.values.get(column)
                if not isinstance(value, (int, float)):
                    warnings.append(
                        f"Run {run.index} ({run.label}) measure {measure.name!r} column "
                        f"{column!r} was skipped because it is not numeric."
                    )
                    continue
                key = (measure.name, measure.analysis, measure.expression, column)
                measure_values.setdefault(key, []).append(float(value))
                run_contributed = True
        if run_contributed:
            measured_run_indexes.add(run.index)
    return measure_values, frozenset(measured_run_indexes)


def _build_measure_summaries(
    measure_values: dict[tuple[str, str, str, str], list[float]],
) -> tuple[ToleranceMeasureSummary, ...]:
    return tuple(
        ToleranceMeasureSummary(
            name=name,
            analysis=analysis,
            expression=expression,
            column=column,
            sample_count=count,
            minimum=minimum,
            maximum=maximum,
            mean=mean,
            stdev=sample_stdev,
        )
        for (name, analysis, expression, column), values in sorted(measure_values.items())
        for count, minimum, maximum, mean, sample_stdev in (_summarize_values(values),)
    )


def summarize_tolerance_analysis(
    batch_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings | None = None,
    measures: tuple[str, ...] | list[str] | None = None,
    refresh_measures: bool = True,
) -> ToleranceAnalysisSummary:
    """Aggregate tolerance-analysis target samples and numeric `.meas` outputs."""

    workspace = workspace_root.resolve(strict=False)
    batch = load_batch_manifest(batch_path, workspace_root=workspace)
    if batch.sweep_kind not in {"monte_carlo", "worst_case"}:
        raise ValueError(
            "summarize_tolerance_analysis requires a Monte Carlo or worst-case batch manifest."
        )
    if batch.plan_path is None:
        raise ValueError("Tolerance-analysis batch manifest is missing its plan_path.")

    prepared = _load_prepared_tolerance_plan(
        batch_plan_path=batch.plan_path,
        sweep_kind=batch.sweep_kind,
        workspace_root=workspace,
    )

    recovered_runs, recovery_warnings = _merge_runs_with_sidecars(
        source_path=batch.source_path,
        output_root=batch.output_root,
        workspace_root=workspace,
        samples=prepared.samples,
        manifest_runs=batch.runs,
    )

    warnings = list(batch.warnings)
    warnings.extend(recovery_warnings)
    successful_runs = [run for run in recovered_runs if run.exit_code == 0]
    failed_run_count = sum(1 for run in recovered_runs if run.exit_code not in (None, 0))
    completed_indexes = {
        run.index for run in recovered_runs if run.exit_code is not None or run.dry_run
    }
    completed_samples = tuple(
        sample for sample in prepared.samples if sample.index in completed_indexes
    )

    parameter_summaries = _build_parameter_summaries(
        prepared.parameter_targets,
        prepared.samples,
        completed_samples,
    )
    component_value_summaries = _build_component_value_summaries(
        prepared.component_targets,
        prepared.samples,
        completed_samples,
    )
    measure_values, measured_run_indexes = _collect_measure_values(
        successful_runs=successful_runs,
        workspace_root=workspace,
        settings=settings,
        measures=measures,
        refresh_measures=refresh_measures,
        warnings=warnings,
    )
    measure_summaries = _build_measure_summaries(measure_values)
    if not measure_summaries:
        warnings.append(
            "No numeric single-row `.meas` values were available to summarize across "
            "successful tolerance-analysis runs."
        )

    completed_run_count = batch.completed_run_count
    if completed_run_count is None:
        completed_run_count = len(recovered_runs)
    completed_run_count = max(completed_run_count, len(completed_indexes))
    pending_run_count = max(batch.run_count - completed_run_count, 0)
    if pending_run_count:
        warnings.append(
            "Tolerance-analysis summary is partial: "
            f"{pending_run_count} planned run(s) are still pending."
        )

    measure_coverage_run_count = len(measured_run_indexes)
    missing_measure_run_count = max(len(successful_runs) - measure_coverage_run_count, 0)
    if missing_measure_run_count:
        warnings.append(
            "Numeric measure coverage only included "
            f"{measure_coverage_run_count} of {len(successful_runs)} successful run(s)."
        )

    completion_pct = (
        0.0 if batch.run_count == 0 else (completed_run_count / batch.run_count) * 100.0
    )
    measure_coverage_pct = (
        0.0 if not successful_runs else (measure_coverage_run_count / len(successful_runs)) * 100.0
    )

    return ToleranceAnalysisSummary(
        batch_path=(batch.manifest_path or batch.output_root / "batch.json").resolve(strict=False),
        plan_path=prepared.plan_path,
        source_path=batch.source_path,
        output_root=batch.output_root,
        sweep_kind=batch.sweep_kind,
        seed=prepared.seed,
        status=batch.status,
        run_count=batch.run_count,
        completed_run_count=completed_run_count,
        successful_run_count=len(successful_runs),
        failed_run_count=failed_run_count,
        pending_run_count=pending_run_count,
        completion_pct=completion_pct,
        measure_coverage_run_count=measure_coverage_run_count,
        missing_measure_run_count=missing_measure_run_count,
        measure_coverage_pct=measure_coverage_pct,
        parameter_summaries=tuple(parameter_summaries),
        component_value_summaries=tuple(component_value_summaries),
        measure_summaries=measure_summaries,
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = [
    "SERVICE_SPEC",
    "ToleranceAnalysisSummary",
    "ToleranceComponentValueSummary",
    "ToleranceMeasureSummary",
    "ToleranceParameterSummary",
    "summarize_tolerance_analysis",
]
