"""Tests for the Monte Carlo preparation, execution, and summary services."""

from __future__ import annotations

import importlib
import json
from datetime import datetime
from pathlib import Path
from shutil import copytree

import pytest

from qspice_mcp.core.exceptions import SandboxViolationError, UnsupportedManifestVersionError
from qspice_mcp.services._internals.persistence_schema import PERSISTED_SCHEMA_VERSION
from qspice_mcp.services._internals.simulation_batch import (
    SimulationBatch,
    SimulationBatchRun,
    save_batch_manifest,
)
from qspice_mcp.services.simulation.prepare_monte_carlo import (
    load_prepared_monte_carlo,
    prepare_monte_carlo,
)
from qspice_mcp.services.simulation.run_monte_carlo import run_monte_carlo
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
prepare_monte_carlo_service = importlib.import_module(
    "qspice_mcp.services.simulation.prepare_monte_carlo"
)
statistical_helpers_service = importlib.import_module(
    "qspice_mcp.services.simulation._statistical_helpers"
)
REPO_ROOT = Path(__file__).resolve().parents[4]
MONTE_CARLO_SUMMARY_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "statistical" / "monte-carlo-summary"
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


def test_prepare_monte_carlo_persists_explicit_plan(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={
            "VIN": {"nominal": 12.0, "tolerance_pct": 10.0},
            "TEMP": {"nominal": 25.0, "tolerance_pct": 20.0},
        },
        sample_count=3,
        seed=7,
    )

    assert prepared.plan_path.is_file()
    assert prepared.parameters[0].minimum == pytest.approx(10.8)
    assert prepared.parameters[1].maximum == pytest.approx(30.0)

    loaded = load_prepared_monte_carlo(prepared.plan_path, workspace_root=tmp_path)

    assert loaded.seed == 7
    assert loaded.samples == prepared.samples


def test_prepare_monte_carlo_stamps_schema_version(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 10.0}},
        sample_count=2,
        seed=3,
    )

    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == PERSISTED_SCHEMA_VERSION


def test_load_prepared_monte_carlo_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 10.0}},
        sample_count=2,
        seed=3,
    )
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    payload["schema_version"] = PERSISTED_SCHEMA_VERSION + 1
    prepared.plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(UnsupportedManifestVersionError, match="unsupported schema_version"):
        load_prepared_monte_carlo(prepared.plan_path, workspace_root=tmp_path)


def test_load_prepared_monte_carlo_rejects_paths_outside_workspace(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 10.0}},
        sample_count=2,
        seed=3,
    )
    payload = json.loads(prepared.plan_path.read_text(encoding="utf-8"))
    payload["source_path"] = str((tmp_path.parent / "escaped.qsch").resolve(strict=False))
    prepared.plan_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(SandboxViolationError, match="outside workspace root"):
        load_prepared_monte_carlo(prepared.plan_path, workspace_root=tmp_path)


def test_prepare_monte_carlo_can_stage_native_mc_schematic(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []

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
        destination.write_text("native mc schematic\n", encoding="utf-8")
        return destination

    monkeypatch.setattr(
        prepare_monte_carlo_service, "open_schematic_editor", fake_open_schematic_editor
    )
    monkeypatch.setattr(
        prepare_monte_carlo_service, "save_edited_schematic", fake_save_edited_schematic
    )

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "tolerance_pct": 1.0}},
        sample_count=2,
        seed=5,
        stage_native_mc=True,
    )

    assert prepared.native_mc_stage is not None
    assert prepared.native_mc_stage.schematic_path.is_file()
    assert prepared.native_mc_stage.parameter_expressions == {"VIN": "mc(12, 0.05)"}
    assert prepared.native_mc_stage.component_value_expressions == {"R1": "mc(1000, 0.01)"}
    assert editor_calls[0].calls == [
        ("set_parameter", ("VIN", "mc(12, 0.05)")),
        ("set_component_value", ("R1", "mc(1000, 0.01)")),
    ]


def test_prepare_monte_carlo_expands_component_presets_and_reference_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    def fake_open_schematic_editor(
        raw_path: str | Path, *, workspace_root: Path
    ) -> tuple[FakeEditor, Path, str]:
        del workspace_root
        return (
            FakeEditor({"R1": "1k", "R2": "2.2k", "C1": "10u"}),
            Path(raw_path).resolve(strict=False),
            "fake",
        )

    monkeypatch.setattr(
        statistical_helpers_service, "open_schematic_editor", fake_open_schematic_editor
    )

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        component_presets={"R": {"tolerance_pct": 5.0}},
        component_values={"R2": {"tolerance_pct": 1.0}},
        sample_count=1,
        seed=13,
    )

    component_targets = {component.reference: component for component in prepared.component_values}
    assert component_targets["R1"].nominal == pytest.approx(1000.0)
    assert component_targets["R1"].tolerance_pct == pytest.approx(5.0)
    assert component_targets["R2"].nominal == pytest.approx(2200.0)
    assert component_targets["R2"].tolerance_pct == pytest.approx(1.0)
    assert "C1" not in component_targets
    assert any("Expanded component preset 'R'" in warning for warning in prepared.warnings)


def test_run_monte_carlo_executes_prepared_assignments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, editor_calls)

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        sample_count=2,
        seed=3,
    )

    result = run_monte_carlo(prepared.plan_path, workspace_root=tmp_path, dry_run=True)

    assert result.sweep_kind == "monte_carlo"
    assert result.plan_path == prepared.plan_path.resolve(strict=False)
    assert result.parameter_names == ("VIN",)
    assert result.run_count == 2
    assert result.runs[0].assignment == {"parameters": prepared.samples[0].parameter_values}
    assert editor_calls[0].calls == [("set_parameter", ("VIN", prepared.samples[0].values["VIN"]))]


def test_run_monte_carlo_supports_component_value_targets(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, editor_calls)

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        sample_count=1,
        seed=2,
    )

    result = run_monte_carlo(prepared.plan_path, workspace_root=tmp_path, dry_run=True)

    assert prepared.component_values[0].reference == "R1"
    assert result.runs[0].assignment == {"component_values": prepared.samples[0].component_values}
    assert editor_calls[0].calls == [
        ("set_component_value", ("R1", prepared.samples[0].component_values["R1"]))
    ]


def test_run_monte_carlo_resume_reuses_successful_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, editor_calls)

    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        sample_count=2,
        seed=3,
    )
    output_root = prepared.output_root
    save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="monte_carlo",
            run_count=2,
            parallelism=1,
            sequential=True,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label=prepared.samples[0].label or "sample-000",
                    assignment={"parameters": dict(prepared.samples[0].parameter_values)},
                    schematic_path=(output_root / "run-000-sample-000" / "demo.qsch").resolve(
                        strict=False
                    ),
                    netlist_path=(output_root / "run-000-sample-000" / "demo.net").resolve(
                        strict=False
                    ),
                    log_path=(output_root / "run-000-sample-000" / "demo.log").resolve(
                        strict=False
                    ),
                    raw_path=(output_root / "run-000-sample-000" / "demo.qraw").resolve(
                        strict=False
                    ),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=True,
                    exit_code=0,
                    duration_s=0.25,
                ),
            ),
            parameter_names=("VIN",),
            status="canceled",
            completed_run_count=1,
            submitted_at=datetime(2026, 5, 6, 9, 0, 0),
            completed_at=datetime(2026, 5, 6, 9, 1, 0),
            plan_path=prepared.plan_path,
            seed=prepared.seed,
        )
    )

    result = run_monte_carlo(
        prepared.plan_path,
        workspace_root=tmp_path,
        dry_run=True,
        resume=True,
    )

    assert result.completed_run_count == 2
    assert result.runs[0].assignment == {"parameters": prepared.samples[0].parameter_values}
    assert result.runs[1].assignment == {"parameters": prepared.samples[1].parameter_values}
    assert len(editor_calls) == 1
    assert editor_calls[0].calls == [
        ("set_parameter", ("VIN", prepared.samples[1].parameter_values["VIN"]))
    ]
    assert any("Reused 1 previously successful run" in warning for warning in result.warnings)


def test_summarize_tolerance_analysis_aggregates_numeric_measures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        sample_count=2,
        seed=11,
    )

    output_root = prepared.output_root
    run_a_dir = output_root / "run-000-sample-000"
    run_b_dir = output_root / "run-001-sample-001"
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
        sweep_kind="monte_carlo",
        run_count=2,
        parallelism=1,
        sequential=True,
        runs=(
            SimulationBatchRun(
                index=0,
                label="sample-000",
                assignment=dict(prepared.samples[0].values),
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
                label="sample-001",
                assignment=dict(prepared.samples[1].values),
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
        batch_id="mc-1",
        status="completed",
        completed_run_count=2,
        submitted_at=datetime(2026, 5, 6, 9, 0, 0),
        completed_at=datetime(2026, 5, 6, 9, 1, 0),
        plan_path=prepared.plan_path,
        seed=prepared.seed,
    )
    persisted = save_batch_manifest(batch)

    values_by_run = {
        "run-000-sample-000": 5.0,
        "run-001-sample-001": 6.0,
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
        persisted.manifest_path or output_root, workspace_root=tmp_path
    )

    assert summary.successful_run_count == 2
    assert summary.parameter_summaries[0].name == "VIN"
    assert summary.measure_summaries[0].name == "vout_avg"
    assert summary.measure_summaries[0].mean == pytest.approx(5.5)


def test_summarize_tolerance_analysis_reports_partial_monte_carlo_progress(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    prepared = prepare_monte_carlo(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        sample_count=3,
        seed=17,
    )

    output_root = prepared.output_root
    run_a_dir = output_root / "run-000-sample-000"
    run_b_dir = output_root / "run-001-sample-001"
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
            sweep_kind="monte_carlo",
            run_count=3,
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="sample-000",
                    assignment={"parameters": dict(prepared.samples[0].parameter_values)},
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
                    label="sample-001",
                    assignment={"parameters": dict(prepared.samples[1].parameter_values)},
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
            batch_id="mc-partial",
            status="running",
            completed_run_count=2,
            submitted_at=datetime(2026, 5, 6, 9, 0, 0),
            plan_path=prepared.plan_path,
            seed=prepared.seed,
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
                    rows=(MeasureRow(step=0, values={"value": 5.1}),),
                ),
            ),
        )

    monkeypatch.setattr(tolerance_summary_service, "read_measures", fake_read_measures)

    summary = summarize_tolerance_analysis(
        persisted.manifest_path or output_root,
        workspace_root=tmp_path,
    )

    completed_values = [
        prepared.samples[0].parameter_values["VIN"],
        prepared.samples[1].parameter_values["VIN"],
    ]
    assert summary.completed_run_count == 2
    assert summary.pending_run_count == 1
    assert summary.completion_pct == pytest.approx((2 / 3) * 100.0)
    assert summary.successful_run_count == 1
    assert summary.failed_run_count == 1
    assert summary.measure_coverage_run_count == 1
    assert summary.missing_measure_run_count == 0
    assert summary.parameter_summaries[0].completed_sample_count == 2
    assert summary.parameter_summaries[0].completed_sampled_min == pytest.approx(
        min(completed_values)
    )
    assert summary.parameter_summaries[0].completed_sampled_max == pytest.approx(
        max(completed_values)
    )
    assert any("summary is partial" in warning for warning in summary.warnings)


def test_summarize_tolerance_analysis_reads_recorded_fixture_without_monkeypatch(
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / MONTE_CARLO_SUMMARY_FIXTURE.name
    copytree(MONTE_CARLO_SUMMARY_FIXTURE, fixture_root)

    summary = summarize_tolerance_analysis(
        fixture_root / "batch.json",
        workspace_root=tmp_path,
        refresh_measures=False,
    )

    assert summary.sweep_kind == "monte_carlo"
    assert summary.run_count == 4
    assert summary.completed_run_count == 4
    assert summary.successful_run_count == 4
    assert summary.failed_run_count == 0
    assert summary.pending_run_count == 0
    assert summary.measure_coverage_run_count == 4
    assert summary.missing_measure_run_count == 0
    assert summary.warnings == ()
    assert summary.parameter_summaries[0].name == "VIN"
    assert summary.parameter_summaries[0].mean == pytest.approx(12.0)
    assert summary.component_value_summaries[0].reference == "R1"
    assert summary.component_value_summaries[0].mean == pytest.approx(1000.0)
    assert summary.measure_summaries[0].name == "vout_avg"
    assert summary.measure_summaries[0].mean == pytest.approx(5.25)
