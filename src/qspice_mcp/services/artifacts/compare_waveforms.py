"""Service for comparing scalar waveform measurements across a batch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import load_batch_manifest
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.measure_waveform import MeasurementOperation, measure_waveform

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.waveform import WaveformComponent
    from qspice_mcp.services._internals.simulation_batch import SimulationBatchRun
    from qspice_mcp.services.waveform.measure_waveform import WaveformMeasurement


@dataclass(frozen=True, slots=True)
class WaveformComparisonRun:
    """One run-level scalar comparison against the selected baseline."""

    run_index: int
    run_label: str
    assignment: dict[str, object]
    raw_path: Path
    step: int | None
    sample_count: int | None
    value: float | None
    delta_from_baseline: float | None
    percent_delta_from_baseline: float | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class WaveformComparison:
    """A scalar waveform comparison across runs in one persisted batch."""

    manifest_path: Path
    batch_id: str | None
    sweep_kind: str
    signal: str
    operation: str
    component: str
    baseline_run_index: int
    baseline_run_label: str
    baseline_value: float
    y_unit: str
    run_count: int
    compared_run_count: int
    runs: tuple[WaveformComparisonRun, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="compare_waveforms",
    title="Compare Waveforms",
    summary="Compare one scalar waveform measurement across runs in a persisted batch.",
    phase="implemented",
)


def compare_waveforms(
    batch_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    operation: MeasurementOperation,
    baseline_run_index: int = 0,
    step: int | None = None,
    step_filters: dict[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
) -> WaveformComparison:
    """Compare a scalar waveform measurement across all runs in one batch."""

    batch = load_batch_manifest(batch_path, workspace_root=workspace_root.resolve(strict=False))
    warnings = list(batch.warnings)
    measured_runs: list[tuple[SimulationBatchRun, WaveformMeasurement | None, str | None]] = []

    for run in batch.runs:
        try:
            measurement = measure_waveform(
                run.raw_path,
                workspace_root=workspace_root.resolve(strict=False),
                signal=signal,
                operation=operation,
                step=step,
                step_filters=step_filters,
                component=component,
                t_start=t_start,
                t_end=t_end,
            )
        except Exception as exc:
            warnings.append(f"Skipped waveform comparison for run {run.index} ({run.label}): {exc}")
            measured_runs.append((run, None, str(exc)))
            continue
        measured_runs.append((run, measurement, None))

    baseline_run: SimulationBatchRun | None = None
    baseline_measurement: WaveformMeasurement | None = None
    for run, run_measurement, error in measured_runs:
        if run.index == baseline_run_index and run_measurement is not None and error is None:
            baseline_run = run
            baseline_measurement = run_measurement
            break
    if baseline_run is None or baseline_measurement is None:
        raise ValueError(
            f"Baseline run {baseline_run_index} could not be measured from the selected batch."
        )

    comparisons: list[WaveformComparisonRun] = []
    compared_run_count = 0
    for run, run_measurement, error in measured_runs:
        if run_measurement is None:
            comparisons.append(
                WaveformComparisonRun(
                    run_index=run.index,
                    run_label=run.label,
                    assignment=dict(run.assignment),
                    raw_path=run.raw_path,
                    step=None,
                    sample_count=None,
                    value=None,
                    delta_from_baseline=None,
                    percent_delta_from_baseline=None,
                    error=error,
                )
            )
            continue

        compared_run_count += 1
        delta = run_measurement.value - baseline_measurement.value
        percent_delta = None
        if baseline_measurement.value != 0:
            percent_delta = delta / baseline_measurement.value * 100.0
        comparisons.append(
            WaveformComparisonRun(
                run_index=run.index,
                run_label=run.label,
                assignment=dict(run.assignment),
                raw_path=run.raw_path,
                step=run_measurement.step,
                sample_count=run_measurement.sample_count,
                value=run_measurement.value,
                delta_from_baseline=delta,
                percent_delta_from_baseline=percent_delta,
                error=None,
            )
        )

    manifest_path = batch.manifest_path or (batch.output_root / "batch.json").resolve(strict=False)
    return WaveformComparison(
        manifest_path=manifest_path,
        batch_id=batch.batch_id,
        sweep_kind=batch.sweep_kind,
        signal=signal,
        operation=operation,
        component=component,
        baseline_run_index=baseline_run.index,
        baseline_run_label=baseline_run.label,
        baseline_value=baseline_measurement.value,
        y_unit=baseline_measurement.y_unit,
        run_count=batch.run_count,
        compared_run_count=compared_run_count,
        runs=tuple(comparisons),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = ["SERVICE_SPEC", "WaveformComparison", "WaveformComparisonRun", "compare_waveforms"]
