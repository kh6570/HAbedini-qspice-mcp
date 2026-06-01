"""Tests for the synchronous simulation sweep services."""

from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path

import pytest

from qspice_mcp.services._internals.simulation_batch import (
    SimulationBatch,
    SimulationBatchRun,
    save_batch_manifest,
    save_batch_run_record,
)
from qspice_mcp.services.simulation.run_model_sweep import run_model_sweep
from qspice_mcp.services.simulation.run_param_sweep import run_param_sweep
from qspice_mcp.services.simulation.run_value_sweep import run_value_sweep

simulation_batch_service = importlib.import_module(
    "qspice_mcp.services._internals.simulation_batch"
)


class FakeEditor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def set_component_value(self, reference: str, value: object) -> None:
        self.calls.append(("set_component_value", (reference, value)))

    def set_parameter(self, name: str, value: object) -> None:
        self.calls.append(("set_parameter", (name, value)))

    def set_element_model(self, reference: str, model: str) -> None:
        self.calls.append(("set_element_model", (reference, model)))


def _patch_batch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    editor_calls: list[FakeEditor],
) -> None:
    def fake_open_schematic_editor(
        raw_path: str | Path, *, workspace_root: Path
    ) -> tuple[FakeEditor, Path, str]:
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


def test_run_value_sweep_composes_edit_generate_and_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    result = run_value_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        values=[1000, 2200],
        parallelism=2,
    )

    assert result.run_count == 2
    assert result.reference == "R1"
    assert result.sequential is False
    assert result.runs[0].assignment == {"R1": 1000}
    assert result.runs[1].assignment == {"R1": 2200}
    assert editor_calls[0].calls == [("set_component_value", ("R1", 1000))]
    assert editor_calls[1].calls == [("set_component_value", ("R1", 2200))]


def test_run_param_sweep_builds_cartesian_product(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    result = run_param_sweep(
        schematic,
        workspace_root=tmp_path,
        parameters={"VIN": [10, 12], "TEMP": [25, 50]},
        dry_run=True,
    )

    assert result.run_count == 4
    assert result.parameter_names == ("VIN", "TEMP")
    assert result.runs[0].assignment == {"VIN": 10, "TEMP": 25}
    assert result.runs[3].assignment == {"VIN": 12, "TEMP": 50}
    assert result.runs[0].dry_run is True
    assert editor_calls[0].calls == [
        ("set_parameter", ("VIN", 10)),
        ("set_parameter", ("TEMP", 25)),
    ]


def test_run_model_sweep_updates_element_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    result = run_model_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="D1",
        models=["1N4148", "BAV21"],
    )

    assert result.run_count == 2
    assert result.reference == "D1"
    assert result.runs[1].assignment == {"D1": "BAV21"}
    assert editor_calls[1].calls == [("set_element_model", ("D1", "BAV21"))]


def test_run_value_sweep_rejects_non_schematic_source(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"require a \.qsch source path"):
        run_value_sweep(netlist, workspace_root=tmp_path, reference="R1", values=[1, 2])


def test_run_value_sweep_resume_reuses_successful_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    output_root = (tmp_path / "resume-output").resolve(strict=False)
    reused_run_dir = output_root / "run-000-r1-1000"
    reused_run_dir.mkdir(parents=True, exist_ok=True)
    for path in (
        reused_run_dir / "demo.qsch",
        reused_run_dir / "demo.net",
        reused_run_dir / "demo.log",
        reused_run_dir / "demo.qraw",
    ):
        path.write_text("artifact\n", encoding="utf-8")
    stale_retry_dir = output_root / "run-001-r1-2200"
    stale_retry_dir.mkdir(parents=True, exist_ok=True)
    stale_retry_marker = stale_retry_dir / "stale.txt"
    stale_retry_marker.write_text("stale\n", encoding="utf-8")
    orphaned_dir = output_root / "run-999-orphan"
    orphaned_dir.mkdir(parents=True, exist_ok=True)
    orphaned_marker = orphaned_dir / "stale.txt"
    orphaned_marker.write_text("stale\n", encoding="utf-8")
    save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=2,
            parallelism=1,
            sequential=True,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="R1=1000",
                    assignment={"R1": 1000},
                    schematic_path=(reused_run_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(reused_run_dir / "demo.net").resolve(strict=False),
                    log_path=(reused_run_dir / "demo.log").resolve(strict=False),
                    raw_path=(reused_run_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.25,
                ),
                SimulationBatchRun(
                    index=1,
                    label="R1=2200",
                    assignment={"R1": 2200},
                    schematic_path=(stale_retry_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(stale_retry_dir / "demo.net").resolve(strict=False),
                    log_path=(stale_retry_dir / "demo.log").resolve(strict=False),
                    raw_path=(stale_retry_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=-1,
                    duration_s=0.1,
                ),
            ),
            reference="R1",
            status="canceled",
            completed_run_count=1,
            submitted_at=datetime(2026, 5, 6, 12, 0, 0),
            completed_at=datetime(2026, 5, 6, 12, 1, 0),
        )
    )

    result = run_value_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        values=[1000, 2200],
        output_dir=output_root,
        resume=True,
    )

    assert result.completed_run_count == 2
    assert result.runs[0].assignment == {"R1": 1000}
    assert result.runs[1].assignment == {"R1": 2200}
    assert len(editor_calls) == 1
    assert editor_calls[0].calls == [("set_component_value", ("R1", 2200))]
    assert stale_retry_marker.exists() is False
    assert orphaned_marker.exists() is False


def test_run_value_sweep_can_preserve_retained_artifacts_on_resume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    output_root = (tmp_path / "retain-output").resolve(strict=False)
    reused_run_dir = output_root / "run-000-r1-1000"
    reused_run_dir.mkdir(parents=True, exist_ok=True)
    for path in (
        reused_run_dir / "demo.qsch",
        reused_run_dir / "demo.net",
        reused_run_dir / "demo.log",
        reused_run_dir / "demo.qraw",
    ):
        path.write_text("artifact\n", encoding="utf-8")
    stale_retry_dir = output_root / "run-001-r1-2200"
    stale_retry_dir.mkdir(parents=True, exist_ok=True)
    stale_retry_marker = stale_retry_dir / "stale.txt"
    stale_retry_marker.write_text("stale\n", encoding="utf-8")
    orphaned_dir = output_root / "run-999-orphan"
    orphaned_dir.mkdir(parents=True, exist_ok=True)
    orphaned_marker = orphaned_dir / "stale.txt"
    orphaned_marker.write_text("stale\n", encoding="utf-8")
    save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=2,
            parallelism=1,
            sequential=True,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="R1=1000",
                    assignment={"R1": 1000},
                    schematic_path=(reused_run_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(reused_run_dir / "demo.net").resolve(strict=False),
                    log_path=(reused_run_dir / "demo.log").resolve(strict=False),
                    raw_path=(reused_run_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.25,
                ),
                SimulationBatchRun(
                    index=1,
                    label="R1=2200",
                    assignment={"R1": 2200},
                    schematic_path=(stale_retry_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(stale_retry_dir / "demo.net").resolve(strict=False),
                    log_path=(stale_retry_dir / "demo.log").resolve(strict=False),
                    raw_path=(stale_retry_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=-1,
                    duration_s=0.1,
                ),
            ),
            reference="R1",
            status="canceled",
            completed_run_count=1,
            submitted_at=datetime(2026, 5, 6, 12, 0, 0),
            completed_at=datetime(2026, 5, 6, 12, 1, 0),
        )
    )

    result = run_value_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        values=[1000, 2200],
        output_dir=output_root,
        resume=True,
        retained_artifact_policy="keep_all",
    )

    assert result.completed_run_count == 2
    assert len(editor_calls) == 1
    assert editor_calls[0].calls == [("set_component_value", ("R1", 2200))]
    assert stale_retry_marker.exists() is True
    assert orphaned_marker.exists() is True
    assert any("Preserved 1 stale run artifact directory" in warning for warning in result.warnings)
    assert any(
        "Preserved 1 orphaned run artifact directory" in warning for warning in result.warnings
    )


def test_run_value_sweep_resume_parallel_handles_sparse_pending_indexes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    completed_indexes: list[int] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    output_root = (tmp_path / "resume-parallel-output").resolve(strict=False)
    reused_run_dir = output_root / "run-000-r1-1000"
    reused_run_dir.mkdir(parents=True, exist_ok=True)
    for path in (
        reused_run_dir / "demo.qsch",
        reused_run_dir / "demo.net",
        reused_run_dir / "demo.log",
        reused_run_dir / "demo.qraw",
    ):
        path.write_text("artifact\n", encoding="utf-8")

    save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=2,
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="R1=1000",
                    assignment={"R1": 1000},
                    schematic_path=(reused_run_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(reused_run_dir / "demo.net").resolve(strict=False),
                    log_path=(reused_run_dir / "demo.log").resolve(strict=False),
                    raw_path=(reused_run_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.25,
                ),
            ),
            batch_id="batch-sparse-parallel",
            status="running",
            completed_run_count=1,
            submitted_at=datetime(2026, 5, 6, 9, 0, 0),
            reference="R1",
        )
    )

    result = run_value_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        values=[1000, 2200],
        output_dir=output_root,
        parallelism=2,
        resume=True,
        on_run_complete=lambda run: completed_indexes.append(run.index),
    )

    assert result.run_count == 2
    assert result.sequential is False
    assert [run.index for run in result.runs] == [0, 1]
    assert completed_indexes == [1]
    assert len(editor_calls) == 1
    assert editor_calls[0].calls == [("set_component_value", ("R1", 2200))]
    assert any("Reused 1 previously successful run" in warning for warning in result.warnings)


def test_run_value_sweep_resume_recovers_completed_run_sidecars(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor_calls: list[FakeEditor] = []
    _patch_batch_dependencies(monkeypatch, tmp_path, editor_calls)

    output_root = (tmp_path / "resume-sidecar-output").resolve(strict=False)
    reused_run_dir = output_root / "run-000-r1-1000"
    recovered_run_dir = output_root / "run-001-r1-2200"
    for run_dir in (reused_run_dir, recovered_run_dir):
        run_dir.mkdir(parents=True, exist_ok=True)
    for path in (
        reused_run_dir / "demo.qsch",
        reused_run_dir / "demo.net",
        reused_run_dir / "demo.log",
        reused_run_dir / "demo.qraw",
        recovered_run_dir / "demo.qsch",
        recovered_run_dir / "demo.net",
        recovered_run_dir / "demo.log",
        recovered_run_dir / "demo.qraw",
    ):
        path.write_text("artifact\n", encoding="utf-8")

    save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=2,
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="R1=1000",
                    assignment={"R1": 1000},
                    schematic_path=(reused_run_dir / "demo.qsch").resolve(strict=False),
                    netlist_path=(reused_run_dir / "demo.net").resolve(strict=False),
                    log_path=(reused_run_dir / "demo.log").resolve(strict=False),
                    raw_path=(reused_run_dir / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.25,
                ),
            ),
            batch_id="batch-sidecar-recovery",
            status="running",
            completed_run_count=1,
            submitted_at=datetime(2026, 5, 6, 9, 0, 0),
            reference="R1",
        )
    )
    save_batch_run_record(
        SimulationBatchRun(
            index=1,
            label="R1=2200",
            assignment={"R1": 2200},
            schematic_path=(recovered_run_dir / "demo.qsch").resolve(strict=False),
            netlist_path=(recovered_run_dir / "demo.net").resolve(strict=False),
            log_path=(recovered_run_dir / "demo.log").resolve(strict=False),
            raw_path=(recovered_run_dir / "demo.qraw").resolve(strict=False),
            command=("QSPICE64.exe", "demo.net"),
            dry_run=False,
            exit_code=0,
            duration_s=0.2,
        )
    )

    result = run_value_sweep(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        values=[1000, 2200],
        output_dir=output_root,
        parallelism=2,
        resume=True,
    )

    assert [run.index for run in result.runs] == [0, 1]
    assert result.completed_run_count == 2
    assert editor_calls == []
    assert any("Recovered 1 completed run" in warning for warning in result.warnings)
