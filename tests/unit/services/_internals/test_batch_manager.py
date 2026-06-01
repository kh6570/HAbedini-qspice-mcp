"""Tests for background batch lifecycle management."""

from __future__ import annotations

import importlib
from datetime import datetime
from pathlib import Path
from threading import Event

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services._internals.simulation_batch import SimulationBatch, save_batch_manifest

batch_manager_service = importlib.import_module("qspice_mcp.services._internals.batch_manager")
telemetry = importlib.import_module("qspice_mcp.infra.telemetry")


class _FakeSpan:
    def __init__(
        self,
        name: str,
        attributes: dict[str, object],
        events: list[tuple[object, ...]],
    ) -> None:
        self._name = name
        self._attributes = attributes
        self._events = events

    def __enter__(self) -> _FakeSpan:
        self._events.append(("enter", self._name, self._attributes))
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._events.append(("exit", self._name))
        return False


class _FakeTracer:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self._events = events

    def start_as_current_span(
        self,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> _FakeSpan:
        return _FakeSpan(name, dict(attributes or {}), self._events)


class _FakeTraceApi:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self._events = events

    def get_tracer(self, name: str) -> _FakeTracer:
        self._events.append(("tracer", name))
        return _FakeTracer(self._events)


def test_batch_manager_submit_and_collect(monkeypatch, tmp_path: Path) -> None:
    def fake_run_value_sweep(
        source_path,
        *,
        workspace_root,
        reference,
        values,
        settings=None,
        output_dir=None,
        parallelism=1,
        dry_run=False,
        timeout_s=None,
        ascii_raw=False,
        extra_switches=(),
        resume=False,
        retained_artifact_policy="cleanup",
        batch_id=None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del (
            workspace_root,
            settings,
            parallelism,
            dry_run,
            timeout_s,
            ascii_raw,
            extra_switches,
            resume,
            retained_artifact_policy,
            should_cancel,
        )
        output_root = Path(output_dir).resolve(strict=False)
        manifest_path = output_root / "batch.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}", encoding="utf-8")
        if on_run_complete is not None:
            on_run_complete(None)
        return SimulationBatch(
            source_path=Path(source_path).resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=len(values),
            parallelism=1,
            sequential=True,
            runs=(),
            reference=reference,
            batch_id=batch_id,
            status="completed",
            completed_run_count=len(values),
            manifest_path=manifest_path.resolve(strict=False),
            submitted_at=datetime.now().astimezone(),
            completed_at=datetime.now().astimezone(),
        )

    monkeypatch.setattr(batch_manager_service, "run_value_sweep", fake_run_value_sweep)

    manager = batch_manager_service.SimulationBatchManager(QSpiceSettings(workspace_root=tmp_path))
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    submitted = manager.submit_batch(
        batch_kind="component_value",
        source_path=str(schematic),
        reference="R1",
        values=[1, 2],
        output_dir=str(tmp_path / "batch-output"),
        resume=True,
        retained_artifact_policy="keep_orphans",
    )

    job = manager._jobs[submitted.batch_id]
    assert job.thread is not None
    job.thread.join(timeout=5)

    status = manager.get_batch_status(submitted.batch_id)
    collected = manager.collect_batch_results(submitted.batch_id)

    assert status.status == "completed"
    assert status.completed_run_count == 2
    assert collected.batch is not None
    assert collected.batch.batch_id == submitted.batch_id


def test_batch_manager_rehydrates_completed_batch_after_restart(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_run_value_sweep(
        source_path,
        *,
        workspace_root,
        reference,
        values,
        settings=None,
        output_dir=None,
        parallelism=1,
        dry_run=False,
        timeout_s=None,
        ascii_raw=False,
        extra_switches=(),
        resume=False,
        retained_artifact_policy="cleanup",
        batch_id=None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del (
            workspace_root,
            settings,
            parallelism,
            dry_run,
            timeout_s,
            ascii_raw,
            extra_switches,
            resume,
            retained_artifact_policy,
            should_cancel,
        )
        output_root = Path(output_dir).resolve(strict=False)
        if on_run_complete is not None:
            on_run_complete(None)
        return save_batch_manifest(
            SimulationBatch(
                source_path=Path(source_path).resolve(strict=False),
                output_root=output_root,
                sweep_kind="component_value",
                run_count=len(values),
                parallelism=1,
                sequential=True,
                runs=(),
                reference=reference,
                batch_id=batch_id,
                status="completed",
                completed_run_count=len(values),
                submitted_at=datetime.now().astimezone(),
                completed_at=datetime.now().astimezone(),
            )
        )

    monkeypatch.setattr(batch_manager_service, "run_value_sweep", fake_run_value_sweep)

    settings = QSpiceSettings(workspace_root=tmp_path)
    manager = batch_manager_service.SimulationBatchManager(settings)
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    submitted = manager.submit_batch(
        batch_kind="component_value",
        source_path=str(schematic),
        reference="R1",
        values=[1, 2],
        output_dir=str(tmp_path / "restart-output"),
    )

    job = manager._jobs[submitted.batch_id]
    assert job.thread is not None
    job.thread.join(timeout=5)

    restarted_manager = batch_manager_service.SimulationBatchManager(settings)
    status = restarted_manager.get_batch_status(submitted.batch_id)
    collected = restarted_manager.collect_batch_results(submitted.batch_id)

    assert status.status == "completed"
    assert status.run_count == 2
    assert status.completed_run_count == 2
    assert collected.batch is not None
    assert collected.batch.batch_id == submitted.batch_id
    assert restarted_manager._jobs[submitted.batch_id].thread is None


def test_batch_manager_rehydrates_legacy_completed_manifest_without_registry(
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    output_root = (tmp_path / "legacy-output").resolve(strict=False)
    persisted = save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=3,
            parallelism=1,
            sequential=True,
            runs=(),
            reference="R1",
            batch_id="batch-012345abcdef",
            status="completed",
            completed_run_count=3,
            submitted_at=datetime.now().astimezone(),
            completed_at=datetime.now().astimezone(),
        )
    )

    manager = batch_manager_service.SimulationBatchManager(QSpiceSettings(workspace_root=tmp_path))
    status = manager.get_batch_status("batch-012345abcdef")
    collected = manager.collect_batch_results("batch-012345abcdef")

    assert status.status == "completed"
    assert status.manifest_path == persisted.manifest_path
    assert collected.batch is not None
    assert collected.batch.output_root == output_root


def test_batch_manager_takes_over_running_batch_after_restart(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def fake_run_value_sweep(
        source_path,
        *,
        workspace_root,
        reference,
        values,
        settings=None,
        output_dir=None,
        parallelism=1,
        dry_run=False,
        timeout_s=None,
        ascii_raw=False,
        extra_switches=(),
        resume=False,
        retained_artifact_policy="cleanup",
        batch_id=None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del settings, should_cancel
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert values == [1, 2]
        assert parallelism == 2
        assert dry_run is False
        assert timeout_s == 9.5
        assert ascii_raw is True
        assert extra_switches == ("-ProtectSelections",)
        assert resume is True
        assert retained_artifact_policy == "keep_orphans"
        output_root = Path(output_dir).resolve(strict=False)
        if on_run_complete is not None:
            on_run_complete(None)
            on_run_complete(None)
        return save_batch_manifest(
            SimulationBatch(
                source_path=Path(source_path).resolve(strict=False),
                output_root=output_root,
                sweep_kind="component_value",
                run_count=2,
                parallelism=parallelism,
                sequential=False,
                runs=(),
                reference=reference,
                batch_id=batch_id,
                status="completed",
                completed_run_count=2,
                submitted_at=datetime.now().astimezone(),
                completed_at=datetime.now().astimezone(),
            )
        )

    monkeypatch.setattr(batch_manager_service, "run_value_sweep", fake_run_value_sweep)

    settings = QSpiceSettings(workspace_root=tmp_path)
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    output_root = (tmp_path / "takeover-output").resolve(strict=False)
    persisted_batch = save_batch_manifest(
        SimulationBatch(
            source_path=schematic.resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=2,
            parallelism=2,
            sequential=False,
            runs=(),
            reference="R1",
            batch_id="batch-012345abcdef",
            status="running",
            completed_run_count=0,
            submitted_at=datetime.now().astimezone(),
        )
    )

    seed_manager = batch_manager_service.SimulationBatchManager(settings)
    seed_job = batch_manager_service._ManagedBatch(
        batch_id="batch-012345abcdef",
        batch_kind="component_value",
        source_path=schematic.resolve(strict=False),
        output_root=output_root,
        manifest_path=persisted_batch.manifest_path or (output_root / "batch.json"),
        submitted_at=datetime.now().astimezone(),
        status="running",
        request=batch_manager_service._ManagedBatchRequest(
            reference="R1",
            values=[1, 2],
            parallelism=2,
            timeout_s=9.5,
            ascii_raw=True,
            extra_switches=("-ProtectSelections",),
            retained_artifact_policy="keep_orphans",
        ),
    )
    seed_manager._persist_job(seed_job)

    restarted_manager = batch_manager_service.SimulationBatchManager(settings)
    status = restarted_manager.get_batch_status("batch-012345abcdef")
    assert status.status in {"running", "completed"}

    job = restarted_manager._jobs["batch-012345abcdef"]
    assert job.thread is not None
    job.thread.join(timeout=5)

    completed = restarted_manager.get_batch_status("batch-012345abcdef")
    collected = restarted_manager.collect_batch_results("batch-012345abcdef")

    assert completed.status == "completed"
    assert completed.completed_run_count == 2
    assert collected.batch is not None
    assert collected.batch.batch_id == "batch-012345abcdef"


def test_batch_manager_cancel_marks_request(monkeypatch, tmp_path: Path) -> None:
    started = Event()
    released = Event()

    def fake_run_value_sweep(
        source_path,
        *,
        workspace_root,
        reference,
        values,
        settings=None,
        output_dir=None,
        parallelism=1,
        dry_run=False,
        timeout_s=None,
        ascii_raw=False,
        extra_switches=(),
        resume=False,
        retained_artifact_policy="cleanup",
        batch_id=None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del (
            source_path,
            workspace_root,
            reference,
            values,
            settings,
            output_dir,
            parallelism,
            dry_run,
            timeout_s,
            ascii_raw,
            extra_switches,
            resume,
            retained_artifact_policy,
            batch_id,
            on_run_complete,
        )
        started.set()
        released.wait(timeout=5)
        return SimulationBatch(
            source_path=tmp_path / "demo.qsch",
            output_root=(tmp_path / "cancel-output").resolve(strict=False),
            sweep_kind="component_value",
            run_count=1,
            parallelism=1,
            sequential=True,
            runs=(),
            reference="R1",
            batch_id="batch-cancel",
            status="canceled" if should_cancel is not None and should_cancel() else "completed",
            completed_run_count=0,
            submitted_at=datetime.now().astimezone(),
            completed_at=datetime.now().astimezone(),
        )

    monkeypatch.setattr(batch_manager_service, "run_value_sweep", fake_run_value_sweep)

    manager = batch_manager_service.SimulationBatchManager(QSpiceSettings(workspace_root=tmp_path))
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    submitted = manager.submit_batch(
        batch_kind="component_value",
        source_path=str(schematic),
        reference="R1",
        values=[1],
        output_dir=str(tmp_path / "cancel-output"),
    )
    assert started.wait(timeout=5)
    cancellation = manager.cancel_batch(submitted.batch_id)
    released.set()
    job = manager._jobs[submitted.batch_id]
    assert job.thread is not None
    job.thread.join(timeout=5)

    assert cancellation.cancellation_requested is True
    assert manager.get_batch_status(submitted.batch_id).status == "canceled"


def test_batch_manager_propagates_trace_context_to_worker_thread(
    monkeypatch,
    tmp_path: Path,
) -> None:
    recorded_events: list[tuple[object, ...]] = []
    captured_trace_id: dict[str, str | None] = {}

    def fake_run_value_sweep(
        source_path,
        *,
        workspace_root,
        reference,
        values,
        settings=None,
        output_dir=None,
        parallelism=1,
        dry_run=False,
        timeout_s=None,
        ascii_raw=False,
        extra_switches=(),
        resume=False,
        retained_artifact_policy="cleanup",
        batch_id=None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del (
            workspace_root,
            reference,
            settings,
            parallelism,
            dry_run,
            timeout_s,
            ascii_raw,
            extra_switches,
            resume,
            retained_artifact_policy,
            should_cancel,
        )
        captured_trace_id["trace_id"] = telemetry.get_current_trace_id()
        output_root = Path(output_dir).resolve(strict=False)
        manifest_path = output_root / "batch.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}", encoding="utf-8")
        if on_run_complete is not None:
            on_run_complete(None)
        return SimulationBatch(
            source_path=Path(source_path).resolve(strict=False),
            output_root=output_root,
            sweep_kind="component_value",
            run_count=len(values),
            parallelism=1,
            sequential=True,
            runs=(),
            reference="R1",
            batch_id=batch_id,
            status="completed",
            completed_run_count=len(values),
            manifest_path=manifest_path.resolve(strict=False),
            submitted_at=datetime.now().astimezone(),
            completed_at=datetime.now().astimezone(),
        )

    monkeypatch.setattr(batch_manager_service, "run_value_sweep", fake_run_value_sweep)
    monkeypatch.setattr(telemetry, "_otel_trace", _FakeTraceApi(recorded_events))

    manager = batch_manager_service.SimulationBatchManager(
        QSpiceSettings(workspace_root=tmp_path, telemetry_enabled=True)
    )
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    with telemetry.request_scope(
        tool_name="submit_batch",
        telemetry_enabled=True,
        long_running=True,
    ) as trace_id:
        submitted = manager.submit_batch(
            batch_kind="component_value",
            source_path=str(schematic),
            reference="R1",
            values=[1, 2],
            output_dir=str(tmp_path / "trace-output"),
        )

    job = manager._jobs[submitted.batch_id]
    assert job.thread is not None
    job.thread.join(timeout=5)

    span_events = [event for event in recorded_events if event[0] == "enter"]
    assert captured_trace_id["trace_id"] == trace_id
    assert any(event[1] == "batch.execute" for event in span_events)
    assert any(
        event[1] == "batch.execute" and event[2]["qspice.trace_id"] == trace_id
        for event in span_events
    )
