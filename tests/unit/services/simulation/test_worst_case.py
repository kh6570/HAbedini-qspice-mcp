"""Tests for the worst-case preparation and execution services."""

from __future__ import annotations

import importlib
import json
from datetime import datetime
from pathlib import Path

import pytest

from qspice_mcp.core.exceptions import SandboxViolationError, UnsupportedManifestVersionError
from qspice_mcp.services._internals.persistence_schema import PERSISTED_SCHEMA_VERSION
from qspice_mcp.services._internals.simulation_batch import (
    SimulationBatch,
    SimulationBatchRun,
    save_batch_manifest,
)
from qspice_mcp.services.simulation.prepare_worst_case import (
    load_prepared_worst_case,
    prepare_worst_case,
)
from qspice_mcp.services.simulation.run_worst_case import run_worst_case
from qspice_mcp.services.simulation.summarize_tolerance_analysis import (
    summarize_tolerance_analysis,
)
from qspice_mcp.services.waveform.read_measures import MeasureRead, MeasureResult, MeasureRow

simulation_batch_service = importlib.import_module(
    "qspice_mcp.services._internals.simulation_batch"
)
tolerance_summary_service = importlib.import_module(
    "qspice_mcp.services.simulation.summarize_tolerance_analysis"
)
prepare_worst_case_service = importlib.import_module(
    "qspice_mcp.services.simulation.prepare_worst_case"
)
statistical_helpers_service = importlib.import_module(
    "qspice_mcp.services.simulation._statistical_helpers"
)


class FakeEditor:
    def __init__(self, component_values: dict[str, str] | None = None) -> None:
        self._component_values = dict(component_values or {})
        self._references = tuple(self._component_values)
        self.calls: list[tuple[str, object]] = []

    def get_components(self, prefixes: str = "*") -> tuple[str, ...]:
        del prefixes
        return self._references

    def get_component_value(self, element: str) -> str:
        return self._component_values[element]

    def set_parameter(self, name: str, value: object) -> None:
        self.calls.append(("set_parameter", (name, value)))

    def set_component_value(self, reference: str, value: object) -> None:
        self.calls.append(("set_component_value", (reference, value)))


def _patch_batch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    editor_calls: list[FakeEditor],
) -> None:
    def fake_open_schematic_editor(
        raw_path: str | Path, *, workspace_root: Path
    ) -> tuple[FakeEditor, Path, str]:
        del workspace_root
        editor = FakeEditor()
        editor_calls.append(editor)
        return editor, Path(raw_path).resolve(strict=False), "fake"

    def fake_save_edited_schematic(
        editor: FakeEditor,
        *,
        schematic_path: Path,
        workspace_root: Path,
        output_path: str | Path | None,
    ) -> Path:
        del editor, workspace_root
        destination = Path(output_path or schematic_path).resolve(strict=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("edited schematic\n", encoding="utf-8")
        return destination

    def fake_generate_netlist(
        raw_path: str | Path, *, workspace_root: Path, output_path: str | Path | None = None
    ):
        del workspace_root
        destination = Path(output_path or Path(raw_path).with_suffix(".net")).resolve(strict=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("* generated\n", encoding="utf-8")
        return type(
            "GeneratedNetlist",
            (),
            {
                "source_path": Path(raw_path).resolve(strict=False),
                "netlist_path": destination,
                "source_kind": "schematic",
                "refreshed": True,
                "copied": False,
                "warnings": ("generated",),
            },
        )()

    def fake_run_simulation(
        netlist_path: str | Path,
        *,
        workspace_root: Path,
        settings: object = None,
        dry_run: bool = False,
        timeout_s: float | None = None,
        log_path: str | Path | None = None,
        raw_output_path: str | Path | None = None,
        extra_switches: tuple[str, ...] = (),
        ascii_raw: bool = False,
    ):
        del workspace_root, settings, timeout_s, extra_switches, ascii_raw
        return type(
            "SimulationRun",
            (),
            {
                "command": ("QSPICE64.exe", str(Path(netlist_path).resolve(strict=False))),
                "netlist_path": Path(netlist_path).resolve(strict=False),
                "log_path": Path(log_path).resolve(strict=False),
                "raw_path": Path(raw_output_path).resolve(strict=False),
                "dry_run": dry_run,
                "exit_code": None if dry_run else 0,
                "duration_s": None if dry_run else 0.25,
            },
        )()

    monkeypatch.setattr(
        simulation_batch_service, "open_schematic_editor", fake_open_schematic_editor
    )
    monkeypatch.setattr(
        simulation_batch_service, "save_edited_schematic", fake_save_edited_schematic
    )
    monkeypatch.setattr(simulation_batch_service, "generate_netlist", fake_generate_netlist)
    monkeypatch.setattr(simulation_batch_service, "run_simulation", fake_run_simulation)


def test_prepare_worst_case_persists_corners_and_nominal(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        include_nominal=True,
        mode="corners",
    )

    assert prepared.plan_path.is_file()
    assert len(prepared.cases) == 5
    assert prepared.cases[0].label == "nominal"
    loaded = load_prepared_worst_case(prepared.plan_path, workspace_root=tmp_path)

    assert loaded.mode == "corners"
    assert loaded.cases[-1].label.startswith("corner-")


def test_prepare_worst_case_stamps_schema_version(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        include_nominal=True,
        mode="corners",
    )

    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == PERSISTED_SCHEMA_VERSION


def test_load_prepared_worst_case_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        include_nominal=True,
        mode="corners",
    )
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    payload["schema_version"] = PERSISTED_SCHEMA_VERSION + 1
    prepared.plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(UnsupportedManifestVersionError, match="unsupported schema_version"):
        load_prepared_worst_case(prepared.plan_path, workspace_root=tmp_path)


def test_load_prepared_worst_case_rejects_paths_outside_workspace(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        include_nominal=True,
        mode="corners",
    )
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    payload["output_root"] = str((tmp_path.parent / "escaped-output").resolve(strict=False))
    prepared.plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(SandboxViolationError, match="outside workspace root"):
        load_prepared_worst_case(prepared.plan_path, workspace_root=tmp_path)


def test_prepare_worst_case_expands_component_presets_and_reference_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    def fake_open_schematic_editor(
        raw_path: str | Path, *, workspace_root: Path
    ) -> tuple[FakeEditor, Path, str]:
        del workspace_root
        return (
            FakeEditor({"R1": "1k", "R2": "4.7k", "C1": "1u"}),
            Path(raw_path).resolve(strict=False),
            "fake",
        )

    monkeypatch.setattr(
        statistical_helpers_service, "open_schematic_editor", fake_open_schematic_editor
    )

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        component_presets={"R": {"tolerance_pct": 5.0}},
        component_values={"R2": {"tolerance_pct": 1.0}},
        include_nominal=False,
        mode="one_at_a_time",
    )

    component_targets = {component.reference: component for component in prepared.component_values}
    assert component_targets["R1"].nominal == pytest.approx(1000.0)
    assert component_targets["R1"].tolerance_pct == pytest.approx(5.0)
    assert component_targets["R2"].nominal == pytest.approx(4700.0)
    assert component_targets["R2"].tolerance_pct == pytest.approx(1.0)
    assert any("Expanded component preset 'R'" in warning for warning in prepared.warnings)


def test_run_worst_case_executes_prepared_assignments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, editor_calls)

    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        include_nominal=False,
        mode="one_at_a_time",
    )

    result = run_worst_case(prepared.plan_path, workspace_root=tmp_path, dry_run=True)

    assert result.sweep_kind == "worst_case"
    assert result.run_count == 4
    assert result.runs[0].assignment == {
        "parameters": prepared.cases[0].parameter_values,
        "component_values": prepared.cases[0].component_values,
    }
    assert editor_calls[0].calls[0][0] == "set_parameter"
    assert editor_calls[0].calls[1][0] == "set_component_value"


def test_summarize_tolerance_analysis_supports_worst_case_and_component_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        include_nominal=False,
        mode="one_at_a_time",
    )

    output_root = prepared.output_root
    run_a_dir = output_root / "run-000-vin-min"
    run_b_dir = output_root / "run-001-vin-max"
    run_a_dir.mkdir(parents=True, exist_ok=True)
    run_b_dir.mkdir(parents=True, exist_ok=True)
    log_a = run_a_dir / "demo.log"
    log_b = run_b_dir / "demo.log"
    raw_a = run_a_dir / "demo.qraw"
    raw_b = run_b_dir / "demo.qraw"
    for path in (log_a, log_b, raw_a, raw_b):
        path.write_text("artifact", encoding="utf-8")

    batch = SimulationBatch(
        source_path=schematic.resolve(strict=False),
        output_root=output_root,
        sweep_kind="worst_case",
        run_count=2,
        parallelism=1,
        sequential=True,
        runs=(
            SimulationBatchRun(
                index=0,
                label=prepared.cases[0].label,
                assignment={
                    "parameters": dict(prepared.cases[0].parameter_values),
                    "component_values": dict(prepared.cases[0].component_values),
                },
                schematic_path=(run_a_dir / "demo.qsch").resolve(strict=False),
                netlist_path=(run_a_dir / "demo.net").resolve(strict=False),
                log_path=log_a.resolve(strict=False),
                raw_path=raw_a.resolve(strict=False),
                command=("QSPICE64.exe", "demo.net"),
                dry_run=False,
                exit_code=0,
                duration_s=0.25,
            ),
            SimulationBatchRun(
                index=1,
                label=prepared.cases[1].label,
                assignment={
                    "parameters": dict(prepared.cases[1].parameter_values),
                    "component_values": dict(prepared.cases[1].component_values),
                },
                schematic_path=(run_b_dir / "demo.qsch").resolve(strict=False),
                netlist_path=(run_b_dir / "demo.net").resolve(strict=False),
                log_path=log_b.resolve(strict=False),
                raw_path=raw_b.resolve(strict=False),
                command=("QSPICE64.exe", "demo.net"),
                dry_run=False,
                exit_code=0,
                duration_s=0.3,
            ),
        ),
        batch_id="wc-1",
        status="completed",
        completed_run_count=2,
        submitted_at=datetime(2026, 5, 6, 10, 0, 0),
        completed_at=datetime(2026, 5, 6, 10, 1, 0),
        plan_path=prepared.plan_path,
    )
    persisted = save_batch_manifest(batch)

    values_by_run = {
        run_a_dir.name: 4.8,
        run_b_dir.name: 5.2,
    }

    def fake_read_measures(
        log_path: str | Path,
        *,
        workspace_root: Path,
        settings: object = None,
        measures: tuple[str, ...] | list[str] | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        refresh_measures: bool = True,
        meas_path: str | Path | None = None,
    ) -> MeasureRead:
        del workspace_root, settings, measures, step, step_filters, refresh_measures, meas_path
        resolved = Path(log_path).resolve(strict=False)
        return MeasureRead(
            log_path=resolved,
            meas_path=resolved.with_suffix(".meas"),
            step_count=1,
            resolved_step=0,
            measures=(
                MeasureResult(
                    name="vout_avg",
                    analysis="tran",
                    expression="avg(V(out))",
                    value_columns=("value",),
                    rows=(
                        MeasureRow(
                            step=0,
                            values={"value": values_by_run[resolved.parent.name]},
                        ),
                    ),
                ),
            ),
        )

    monkeypatch.setattr(tolerance_summary_service, "read_measures", fake_read_measures)

    summary = summarize_tolerance_analysis(
        persisted.manifest_path or output_root,
        workspace_root=tmp_path,
    )

    assert summary.sweep_kind == "worst_case"
    assert summary.seed is None
    assert summary.parameter_summaries[0].name == "VIN"
    assert summary.component_value_summaries[0].reference == "R1"
    assert summary.measure_summaries[0].mean == pytest.approx(5.0)


def test_summarize_tolerance_analysis_reports_partial_worst_case_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    prepared = prepare_worst_case(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        include_nominal=False,
        mode="one_at_a_time",
    )

    output_root = prepared.output_root
    run_a_dir = output_root / f"run-000-{prepared.cases[0].label}"
    run_b_dir = output_root / f"run-001-{prepared.cases[1].label}"
    run_a_dir.mkdir(parents=True, exist_ok=True)
    run_b_dir.mkdir(parents=True, exist_ok=True)
    log_a = run_a_dir / "demo.log"
    raw_a = run_a_dir / "demo.qraw"
    log_b = run_b_dir / "demo.log"
    raw_b = run_b_dir / "demo.qraw"
    for path in (log_a, raw_a, log_b, raw_b):
        path.write_text("artifact", encoding="utf-8")

    persisted = save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="worst_case",
            run_count=len(prepared.cases),
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label=prepared.cases[0].label,
                    assignment={
                        "parameters": dict(prepared.cases[0].parameter_values),
                        "component_values": dict(prepared.cases[0].component_values),
                    },
                    schematic_path=(run_a_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(run_a_dir / "demo.net").resolve(strict=False),
                    log_path=log_a.resolve(strict=False),
                    raw_path=raw_a.resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.2,
                ),
                SimulationBatchRun(
                    index=1,
                    label=prepared.cases[1].label,
                    assignment={
                        "parameters": dict(prepared.cases[1].parameter_values),
                        "component_values": dict(prepared.cases[1].component_values),
                    },
                    schematic_path=(run_b_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(run_b_dir / "demo.net").resolve(strict=False),
                    log_path=log_b.resolve(strict=False),
                    raw_path=raw_b.resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=-1,
                    duration_s=0.3,
                    warnings=("failed",),
                ),
            ),
            batch_id="wc-partial",
            status="running",
            completed_run_count=2,
            submitted_at=datetime(2026, 5, 6, 10, 0, 0),
            plan_path=prepared.plan_path,
        )
    )

    def fake_read_measures(
        log_path: str | Path,
        *,
        workspace_root: Path,
        settings: object = None,
        measures: tuple[str, ...] | list[str] | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        refresh_measures: bool = True,
        meas_path: str | Path | None = None,
    ) -> MeasureRead:
        del workspace_root, settings, measures, step, step_filters, refresh_measures, meas_path
        resolved = Path(log_path).resolve(strict=False)
        return MeasureRead(
            log_path=resolved,
            meas_path=resolved.with_suffix(".meas"),
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

    monkeypatch.setattr(tolerance_summary_service, "read_measures", fake_read_measures)

    summary = summarize_tolerance_analysis(
        persisted.manifest_path or output_root,
        workspace_root=tmp_path,
    )

    completed_component_values = [
        prepared.cases[0].component_values["R1"],
        prepared.cases[1].component_values["R1"],
    ]
    assert summary.pending_run_count == len(prepared.cases) - 2
    assert summary.completion_pct == pytest.approx((2 / len(prepared.cases)) * 100.0)
    assert summary.component_value_summaries[0].completed_sample_count == 2
    assert summary.component_value_summaries[0].completed_sampled_min == pytest.approx(
        min(completed_component_values)
    )
    assert summary.component_value_summaries[0].completed_sampled_max == pytest.approx(
        max(completed_component_values)
    )
    assert summary.measure_coverage_run_count == 1
    assert summary.missing_measure_run_count == 0
    assert any("summary is partial" in warning for warning in summary.warnings)
