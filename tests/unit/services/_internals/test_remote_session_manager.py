"""Tests for remote-style simulation lifecycle management."""

from __future__ import annotations

import importlib
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services._internals.persistence_schema import PERSISTED_SCHEMA_VERSION
from qspice_mcp.services.simulation.run_simulation import SimulationRun

remote_manager_service = importlib.import_module(
    "qspice_mcp.services._internals.remote_session_manager"
)
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


def test_remote_session_manager_submit_download_and_close(monkeypatch, tmp_path: Path) -> None:
    def fake_run_simulation(
        netlist_path,
        *,
        workspace_root,
        settings=None,
        dry_run=False,
        timeout_s=None,
        log_path=None,
        raw_output_path=None,
        extra_switches=(),
        ascii_raw=False,
    ) -> SimulationRun:
        del workspace_root, settings, dry_run, timeout_s, extra_switches, ascii_raw
        resolved_netlist = Path(netlist_path).resolve(strict=False)
        resolved_log = Path(log_path).resolve(strict=False)
        resolved_raw = Path(raw_output_path).resolve(strict=False)
        resolved_log.write_text("log\n", encoding="utf-8")
        resolved_raw.write_text("raw\n", encoding="utf-8")
        return SimulationRun(
            adapter_key="cli",
            command=("QSPICE64.exe", str(resolved_netlist)),
            working_directory=resolved_netlist.parent,
            netlist_path=resolved_netlist,
            log_path=resolved_log,
            raw_path=resolved_raw,
            dry_run=False,
            started_at=datetime.now().astimezone(),
            exit_code=0,
            duration_s=0.2,
            log_exists=True,
            raw_exists=True,
        )

    monkeypatch.setattr(remote_manager_service, "run_simulation", fake_run_simulation)

    manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    submitted = manager.submit_remote_simulation(source_path=str(netlist))
    session = manager._sessions[submitted.session_id]
    assert session.thread is not None
    session.thread.join(timeout=5)

    status = manager.poll_remote_run(submitted.session_id)
    bundle = manager.download_remote_artifacts(submitted.session_id)

    assert status.status == "completed"
    assert status.owner_host_id is not None
    assert status.raw_available is True
    assert bundle.artifact_count == 4
    assert bundle.output_path.is_file() is True
    with ZipFile(bundle.output_path) as archive:
        names = set(archive.namelist())
        assert "session.json" in names
        assert "netlist/demo.net" in names
        assert "artifacts/demo.log" in names
        assert "artifacts/demo.qraw" in names
        summary = json.loads(archive.read("session.json").decode("utf-8"))
    assert summary["schema_version"] == PERSISTED_SCHEMA_VERSION
    assert summary["status"] == "completed"

    closure = manager.close_remote_session(submitted.session_id, delete_bundle=True)
    assert closure.status == "closed"
    assert closure.bundle_deleted is True
    assert bundle.output_path.exists() is False


def test_remote_session_manager_reloads_completed_session_from_disk(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_simulation(
        netlist_path,
        *,
        workspace_root,
        settings=None,
        dry_run=False,
        timeout_s=None,
        log_path=None,
        raw_output_path=None,
        extra_switches=(),
        ascii_raw=False,
    ) -> SimulationRun:
        del workspace_root, settings, dry_run, timeout_s, extra_switches, ascii_raw
        resolved_netlist = Path(netlist_path).resolve(strict=False)
        resolved_log = Path(log_path).resolve(strict=False)
        resolved_raw = Path(raw_output_path).resolve(strict=False)
        resolved_log.write_text("log\n", encoding="utf-8")
        resolved_raw.write_text("raw\n", encoding="utf-8")
        return SimulationRun(
            adapter_key="cli",
            command=("QSPICE64.exe", str(resolved_netlist)),
            working_directory=resolved_netlist.parent,
            netlist_path=resolved_netlist,
            log_path=resolved_log,
            raw_path=resolved_raw,
            dry_run=False,
            started_at=datetime.now().astimezone(),
            exit_code=0,
            duration_s=0.2,
            log_exists=True,
            raw_exists=True,
        )

    monkeypatch.setattr(remote_manager_service, "run_simulation", fake_run_simulation)

    first_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    submitted = first_manager.submit_remote_simulation(source_path=str(netlist))
    session = first_manager._sessions[submitted.session_id]
    assert session.thread is not None
    session.thread.join(timeout=5)

    second_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    status = second_manager.poll_remote_run(submitted.session_id)
    bundle = second_manager.download_remote_artifacts(submitted.session_id)
    assert bundle.output_path.is_file() is True
    closure = second_manager.close_remote_session(submitted.session_id, delete_bundle=True)

    assert status.status == "completed"
    assert status.raw_available is True
    assert closure.status == "closed"

    third_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    reloaded = third_manager.poll_remote_run(submitted.session_id)
    assert reloaded.status == "closed"
    assert reloaded.bundle_available is False


def test_remote_session_manager_marks_orphaned_running_session_after_restart(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    output_root = (tmp_path / "artifacts" / "remote" / "demo-remote-deadbeefcafe").resolve(
        strict=False
    )
    output_root.mkdir(parents=True, exist_ok=True)

    seed_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    orphaned = remote_manager_service._ManagedRemoteSession(
        session_id="remote-deadbeefcafe",
        source_path=netlist.resolve(strict=False),
        output_root=output_root,
        submitted_at=datetime.now().astimezone(),
        status="running",
        owner_host_id=seed_manager._manager_host_id,
        owner_instance_id="remote-manager-oldowner",
        owner_pid=424242,
        lease_heartbeat_at=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
    )
    seed_manager._persist_session(orphaned)

    monkeypatch.setattr(remote_manager_service, "_pid_exists", lambda pid: False)

    restarted = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    status = restarted.poll_remote_run("remote-deadbeefcafe")

    assert status.status == "failed"
    assert status.error is not None
    assert "orphaned" in status.error.lower()


def test_remote_session_manager_keeps_fresh_running_session_owned_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    output_root = (tmp_path / "artifacts" / "remote" / "demo-remote-feedfacecafe").resolve(
        strict=False
    )
    output_root.mkdir(parents=True, exist_ok=True)

    seed_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    foreign_host_id = f"{seed_manager._manager_host_id}-other"
    running = remote_manager_service._ManagedRemoteSession(
        session_id="remote-feedfacecafe",
        source_path=netlist.resolve(strict=False),
        output_root=output_root,
        submitted_at=datetime.now().astimezone(),
        status="running",
        owner_host_id=foreign_host_id,
        owner_instance_id="remote-manager-activeowner",
        owner_pid=987654,
        lease_heartbeat_at=datetime.now().astimezone(),
    )
    seed_manager._persist_session(running)

    monkeypatch.setattr(remote_manager_service, "_pid_exists", lambda pid: False)

    restarted = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    status = restarted.poll_remote_run("remote-feedfacecafe")

    assert status.status == "running"
    assert status.owner_host_id == foreign_host_id
    assert status.error is None


def test_remote_session_manager_marks_stale_foreign_host_session_orphaned(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    output_root = (tmp_path / "artifacts" / "remote" / "demo-remote-cafebabefeed").resolve(
        strict=False
    )
    output_root.mkdir(parents=True, exist_ok=True)

    seed_manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    foreign_host_id = f"{seed_manager._manager_host_id}-other"
    running = remote_manager_service._ManagedRemoteSession(
        session_id="remote-cafebabefeed",
        source_path=netlist.resolve(strict=False),
        output_root=output_root,
        submitted_at=datetime.now().astimezone(),
        status="running",
        owner_host_id=foreign_host_id,
        owner_instance_id="remote-manager-foreignowner",
        owner_pid=123456,
        lease_heartbeat_at=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
    )
    seed_manager._persist_session(running)

    monkeypatch.setattr(remote_manager_service, "_pid_exists", lambda pid: True)

    restarted = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    status = restarted.poll_remote_run("remote-cafebabefeed")

    assert status.status == "failed"
    assert status.owner_host_id == foreign_host_id
    assert status.error is not None
    assert foreign_host_id in status.error


def test_remote_session_manager_rejects_non_empty_output_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        remote_manager_service,
        "run_simulation",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unreachable")),
    )
    manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    occupied = tmp_path / "occupied-remote-output"
    occupied.mkdir(parents=True)
    (occupied / "stale.txt").write_text("stale\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="execution-isolated"):
        manager.submit_remote_simulation(
            source_path=str(netlist),
            output_dir=str(occupied),
        )


def test_remote_session_manager_rejects_non_zip_bundle_paths(monkeypatch, tmp_path: Path) -> None:
    def fake_run_simulation(
        netlist_path,
        *,
        workspace_root,
        settings=None,
        dry_run=False,
        timeout_s=None,
        log_path=None,
        raw_output_path=None,
        extra_switches=(),
        ascii_raw=False,
    ) -> SimulationRun:
        del workspace_root, settings, dry_run, timeout_s, extra_switches, ascii_raw
        resolved_netlist = Path(netlist_path).resolve(strict=False)
        resolved_log = Path(log_path).resolve(strict=False)
        resolved_raw = Path(raw_output_path).resolve(strict=False)
        resolved_log.write_text("log\n", encoding="utf-8")
        resolved_raw.write_text("raw\n", encoding="utf-8")
        return SimulationRun(
            adapter_key="cli",
            command=("QSPICE64.exe", str(resolved_netlist)),
            working_directory=resolved_netlist.parent,
            netlist_path=resolved_netlist,
            log_path=resolved_log,
            raw_path=resolved_raw,
            dry_run=False,
            started_at=datetime.now().astimezone(),
            exit_code=0,
            duration_s=0.2,
            log_exists=True,
            raw_exists=True,
        )

    monkeypatch.setattr(remote_manager_service, "run_simulation", fake_run_simulation)

    manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    submitted = manager.submit_remote_simulation(source_path=str(netlist))
    session = manager._sessions[submitted.session_id]
    assert session.thread is not None
    session.thread.join(timeout=5)

    with pytest.raises(ValidationError, match=r"\.zip"):
        manager.download_remote_artifacts(
            submitted.session_id,
            output_path=str(tmp_path / "bundle.txt"),
        )


def test_remote_session_manager_propagates_trace_context_to_worker_thread(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    recorded_events: list[tuple[object, ...]] = []
    captured_trace_id: dict[str, str | None] = {}

    def fake_run_simulation(
        netlist_path,
        *,
        workspace_root,
        settings=None,
        dry_run=False,
        timeout_s=None,
        log_path=None,
        raw_output_path=None,
        extra_switches=(),
        ascii_raw=False,
    ) -> SimulationRun:
        del workspace_root, settings, dry_run, timeout_s, extra_switches, ascii_raw
        captured_trace_id["trace_id"] = telemetry.get_current_trace_id()
        resolved_netlist = Path(netlist_path).resolve(strict=False)
        resolved_log = Path(log_path).resolve(strict=False)
        resolved_raw = Path(raw_output_path).resolve(strict=False)
        resolved_log.write_text("log\n", encoding="utf-8")
        resolved_raw.write_text("raw\n", encoding="utf-8")
        return SimulationRun(
            adapter_key="cli",
            command=("QSPICE64.exe", str(resolved_netlist)),
            working_directory=resolved_netlist.parent,
            netlist_path=resolved_netlist,
            log_path=resolved_log,
            raw_path=resolved_raw,
            dry_run=False,
            started_at=datetime.now().astimezone(),
            exit_code=0,
            duration_s=0.2,
            log_exists=True,
            raw_exists=True,
        )

    monkeypatch.setattr(remote_manager_service, "run_simulation", fake_run_simulation)
    monkeypatch.setattr(telemetry, "_otel_trace", _FakeTraceApi(recorded_events))

    manager = remote_manager_service.RemoteSimulationManager(
        QSpiceSettings(workspace_root=tmp_path, telemetry_enabled=True)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    with telemetry.request_scope(
        tool_name="submit_remote_simulation",
        telemetry_enabled=True,
        long_running=True,
    ) as trace_id:
        submitted = manager.submit_remote_simulation(source_path=str(netlist))

    session = manager._sessions[submitted.session_id]
    assert session.thread is not None
    session.thread.join(timeout=5)

    span_events = [event for event in recorded_events if event[0] == "enter"]
    assert captured_trace_id["trace_id"] == trace_id
    assert any(event[1] == "remote.execute" for event in span_events)
    assert any(
        event[1] == "remote.execute" and event[2]["qspice.trace_id"] == trace_id
        for event in span_events
    )
