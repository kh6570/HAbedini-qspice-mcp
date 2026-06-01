"""Service for exporting batch measures to a CSV artifact."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import load_batch_manifest
from qspice_mcp.services._shared.paths import resolve_workspace_output_path
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_measures import read_measures

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class MeasureCsvExport:
    """Metadata for one exported batch measures CSV."""

    manifest_path: Path
    batch_id: str | None
    output_path: Path
    run_count: int
    exported_run_count: int
    row_count: int
    columns: tuple[str, ...]
    measure_names: tuple[str, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="export_measures_csv",
    title="Export Measures CSV",
    summary="Export measurement rows from a persisted batch manifest to CSV.",
    phase="implemented",
    read_only=False,
)


def _csv_cell(value: object | None) -> object:
    """Render one CSV-friendly scalar value."""

    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def export_measures_csv(
    batch_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    measures: tuple[str, ...] | list[str] | None = None,
    refresh_measures: bool = True,
) -> MeasureCsvExport:
    """Export measurement rows from one persisted batch manifest to CSV."""

    workspace = workspace_root.resolve(strict=False)
    batch = load_batch_manifest(batch_path, workspace_root=workspace)
    destination = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace,
        default=batch.output_root / "measures.csv",
        suffixes=(".csv",),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)

    assignment_columns = tuple(
        f"assignment_{name}"
        for name in sorted({str(key) for run in batch.runs for key in run.assignment})
    )
    warnings = list(batch.warnings)
    rendered_rows: list[dict[str, object]] = []
    value_columns: set[str] = set()
    measure_names_seen: set[str] = set()
    exported_run_count = 0

    for run in batch.runs:
        try:
            inspection = read_measures(
                run.log_path,
                workspace_root=workspace,
                measures=measures,
                refresh_measures=refresh_measures,
            )
        except Exception as exc:
            warnings.append(f"Skipped measure export for run {run.index} ({run.label}): {exc}")
            continue

        exported_run_count += 1
        for measure in inspection.measures:
            measure_names_seen.add(measure.name)
            prefixed_value_columns = tuple(f"value_{name}" for name in measure.value_columns)
            value_columns.update(prefixed_value_columns)
            for row in measure.rows:
                rendered = {
                    "batch_id": _csv_cell(batch.batch_id),
                    "sweep_kind": batch.sweep_kind,
                    "run_index": run.index,
                    "run_label": run.label,
                    "step": _csv_cell(row.step),
                    "measure_name": measure.name,
                    "analysis": measure.analysis,
                    "expression": measure.expression,
                    "log_path": str(run.log_path),
                    "meas_path": str(inspection.meas_path)
                    if inspection.meas_path is not None
                    else "",
                    "exit_code": _csv_cell(run.exit_code),
                    "duration_s": _csv_cell(run.duration_s),
                }
                for column in assignment_columns:
                    name = column.removeprefix("assignment_")
                    rendered[column] = _csv_cell(run.assignment.get(name))
                for column_name in measure.value_columns:
                    rendered[f"value_{column_name}"] = _csv_cell(row.values.get(column_name))
                rendered_rows.append(rendered)

    if not rendered_rows:
        raise ValueError("No measure rows were available for export from the selected batch.")

    columns = (
        "batch_id",
        "sweep_kind",
        "run_index",
        "run_label",
        "step",
        "measure_name",
        "analysis",
        "expression",
        "log_path",
        "meas_path",
        "exit_code",
        "duration_s",
        *assignment_columns,
        *tuple(sorted(value_columns)),
    )
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rendered_rows)

    manifest_path = batch.manifest_path or (batch.output_root / "batch.json").resolve(strict=False)
    return MeasureCsvExport(
        manifest_path=manifest_path,
        batch_id=batch.batch_id,
        output_path=destination,
        run_count=batch.run_count,
        exported_run_count=exported_run_count,
        row_count=len(rendered_rows),
        columns=columns,
        measure_names=tuple(sorted(measure_names_seen)),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = ["SERVICE_SPEC", "MeasureCsvExport", "export_measures_csv"]
