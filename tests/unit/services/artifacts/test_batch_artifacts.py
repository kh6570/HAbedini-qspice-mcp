"""Tests for persisted batch artifact services."""

from __future__ import annotations

import csv
import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from qspice_mcp.core.exceptions import (
    SandboxViolationError,
    UnsupportedManifestVersionError,
    ValidationError,
)
from qspice_mcp.services._internals.persistence_schema import PERSISTED_SCHEMA_VERSION
from qspice_mcp.services._internals.simulation_batch import (
    SimulationBatch,
    SimulationBatchRun,
    load_batch_manifest,
    save_batch_manifest,
)
from qspice_mcp.services.artifacts.compare_waveforms import compare_waveforms
from qspice_mcp.services.artifacts.export_measures_csv import export_measures_csv
from qspice_mcp.services.artifacts.summarize_batch import summarize_batch
from qspice_mcp.services.waveform.measure_waveform import WaveformMeasurement
from qspice_mcp.services.waveform.read_measures import MeasureRead, MeasureResult, MeasureRow

compare_waveforms_service = importlib.import_module(
    "qspice_mcp.services.artifacts.compare_waveforms"
)
export_measures_csv_service = importlib.import_module(
    "qspice_mcp.services.artifacts.export_measures_csv"
)


def _persist_batch(tmp_path: Path) -> Path:
    output_root = tmp_path / "artifacts" / "batch-a"
    run_a_dir = output_root / "run-000-a"
    run_b_dir = output_root / "run-001-b"
    run_a_dir.mkdir(parents=True, exist_ok=True)
    run_b_dir.mkdir(parents=True, exist_ok=True)

    source_path = tmp_path / "buck.qsch"
    source_path.write_text("schematic", encoding="utf-8")

    log_a = run_a_dir / "buck.log"
    raw_a = run_a_dir / "buck.qraw"
    log_b = run_b_dir / "buck.log"
    raw_b = run_b_dir / "buck.qraw"
    for path in (log_a, raw_a, log_b, raw_b):
        path.write_text("artifact", encoding="utf-8")

    batch = SimulationBatch(
        source_path=source_path.resolve(strict=False),
        output_root=output_root.resolve(strict=False),
        sweep_kind="component_value",
        run_count=2,
        parallelism=1,
        sequential=True,
        runs=(
            SimulationBatchRun(
                index=0,
                label="R4=10",
                assignment={"value": 10},
                schematic_path=(run_a_dir / "buck.qsch").resolve(strict=False),
                netlist_path=(run_a_dir / "buck.net").resolve(strict=False),
                log_path=log_a.resolve(strict=False),
                raw_path=raw_a.resolve(strict=False),
                command=("QSPICE64.exe", "buck.net"),
                dry_run=False,
                exit_code=0,
                duration_s=0.25,
            ),
            SimulationBatchRun(
                index=1,
                label="R4=100",
                assignment={"value": 100},
                schematic_path=(run_b_dir / "buck.qsch").resolve(strict=False),
                netlist_path=(run_b_dir / "buck.net").resolve(strict=False),
                log_path=log_b.resolve(strict=False),
                raw_path=raw_b.resolve(strict=False),
                command=("QSPICE64.exe", "buck.net"),
                dry_run=False,
                exit_code=0,
                duration_s=0.3,
            ),
        ),
        batch_id="batch-a",
        status="completed",
        completed_run_count=2,
        submitted_at=datetime(2026, 4, 30, 12, 0, 0),
        completed_at=datetime(2026, 4, 30, 12, 1, 0),
    )
    persisted = save_batch_manifest(batch)
    assert persisted.manifest_path is not None
    return persisted.manifest_path


def test_summarize_batch_reports_artifacts(tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)

    summary = summarize_batch(manifest_path, workspace_root=tmp_path)

    assert summary.batch_id == "batch-a"
    assert summary.run_count == 2
    assert summary.successful_run_count == 2
    assert summary.runs[0].log_available is True
    assert summary.runs[1].raw_available is True


def test_save_batch_manifest_stamps_schema_version(tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == PERSISTED_SCHEMA_VERSION


def test_load_batch_manifest_accepts_legacy_unversioned_payload(tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload.pop("schema_version")
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    loaded = load_batch_manifest(manifest_path, workspace_root=tmp_path)

    assert loaded.batch_id == "batch-a"


def test_load_batch_manifest_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["schema_version"] = PERSISTED_SCHEMA_VERSION + 1
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(UnsupportedManifestVersionError, match="unsupported schema_version"):
        load_batch_manifest(manifest_path, workspace_root=tmp_path)


def test_load_batch_manifest_rejects_embedded_paths_outside_workspace(tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["source_path"] = str((tmp_path.parent / "escaped.qsch").resolve(strict=False))
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(SandboxViolationError, match="outside workspace root"):
        load_batch_manifest(manifest_path, workspace_root=tmp_path)


def test_export_measures_csv_flattens_measure_rows(monkeypatch, tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)
    output_path = tmp_path / "summary" / "measures.csv"

    def fake_read_measures(
        log_path: str | Path,
        *,
        workspace_root: Path,
        measures: tuple[str, ...] | list[str] | None = None,
        refresh_measures: bool = True,
    ) -> MeasureRead:
        del workspace_root, measures, refresh_measures
        return MeasureRead(
            log_path=Path(log_path).resolve(strict=False),
            meas_path=Path(log_path).with_suffix(".meas").resolve(strict=False),
            step_count=1,
            resolved_step=0,
            measures=(
                MeasureResult(
                    name="vout_avg",
                    analysis="tran",
                    expression="avg(V(out))",
                    value_columns=("value",),
                    rows=(MeasureRow(step=0, values={"value": 5.0}),),
                ),
            ),
        )

    monkeypatch.setattr(export_measures_csv_service, "read_measures", fake_read_measures)

    export = export_measures_csv(manifest_path, workspace_root=tmp_path, output_path=output_path)

    assert export.row_count == 2
    assert export.output_path == output_path.resolve(strict=False)
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["measure_name"] == "vout_avg"
    assert rows[0]["assignment_value"] == "10"
    assert rows[1]["value_value"] == "5.0"


def test_export_measures_csv_rejects_non_csv_output_paths(monkeypatch, tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)

    def fake_read_measures(
        log_path: str | Path,
        *,
        workspace_root: Path,
        measures: tuple[str, ...] | list[str] | None = None,
        refresh_measures: bool = True,
    ) -> MeasureRead:
        del log_path, workspace_root, measures, refresh_measures
        return MeasureRead(
            log_path=(tmp_path / "demo.log").resolve(strict=False),
            meas_path=(tmp_path / "demo.meas").resolve(strict=False),
            step_count=1,
            resolved_step=0,
            measures=(
                MeasureResult(
                    name="vout_avg",
                    analysis="tran",
                    expression="avg(V(out))",
                    value_columns=("value",),
                    rows=(MeasureRow(step=0, values={"value": 5.0}),),
                ),
            ),
        )

    monkeypatch.setattr(export_measures_csv_service, "read_measures", fake_read_measures)

    with pytest.raises(ValidationError, match=r"\.csv"):
        export_measures_csv(
            manifest_path,
            workspace_root=tmp_path,
            output_path=tmp_path / "summary" / "measures.txt",
        )


def test_compare_waveforms_measures_delta_from_baseline(monkeypatch, tmp_path: Path) -> None:
    manifest_path = _persist_batch(tmp_path)

    values_by_run = {
        "run-000-a": 5.0,
        "run-001-b": 7.5,
    }

    def fake_measure_waveform(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        signal: str,
        operation: str,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: str = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> WaveformMeasurement:
        del workspace_root, step, step_filters, component, t_start, t_end
        raw = Path(raw_path).resolve(strict=False)
        return WaveformMeasurement(
            raw_path=raw,
            plot_name="Transient Analysis",
            axis_name="time",
            signal=signal,
            step=0,
            component="real",
            operation=operation,
            sample_count=100,
            x_unit="s",
            y_unit="V",
            value=values_by_run[raw.parent.name],
        )

    monkeypatch.setattr(compare_waveforms_service, "measure_waveform", fake_measure_waveform)

    comparison = compare_waveforms(
        manifest_path,
        workspace_root=tmp_path,
        signal="V(out)",
        operation="max",
    )

    assert comparison.baseline_value == 5.0
    assert comparison.compared_run_count == 2
    assert comparison.runs[0].delta_from_baseline == 0.0
    assert comparison.runs[1].delta_from_baseline == 2.5
    assert comparison.runs[1].percent_delta_from_baseline == 50.0
