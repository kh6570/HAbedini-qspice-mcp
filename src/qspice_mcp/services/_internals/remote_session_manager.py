"""In-memory remote-style simulation lifecycle and artifact transport manager."""

from __future__ import annotations

import json
import os
import shutil
import socket
from contextvars import copy_context
from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING, Literal, cast
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra.logging import get_logger
from qspice_mcp.infra.telemetry import operation_span
from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._internals.simulation_batch import slugify
from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
    resolve_workspace_path,
    validate_existing_file,
)
from qspice_mcp.services.remote.close_remote_session import RemoteSessionClosure
from qspice_mcp.services.remote.download_remote_artifacts import RemoteArtifactDownload
from qspice_mcp.services.remote.poll_remote_run import RemoteRunStatus
from qspice_mcp.services.remote.submit_remote_simulation import RemoteSimulationSubmission
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.run_simulation import SimulationRun, run_simulation

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

RemoteSessionState = Literal["queued", "running", "completed", "failed", "closed"]
RemoteArtifactKind = Literal["summary", "source", "netlist", "log", "raw"]

_DEFAULT_ARTIFACT_KINDS: tuple[RemoteArtifactKind, ...] = ("summary", "netlist", "log", "raw")
_VALID_ARTIFACT_KINDS = frozenset((*_DEFAULT_ARTIFACT_KINDS, "source"))
_REMOTE_SESSION_ID_PATTERN = r"remote-[0-9a-f]{12}"
_REMOTE_SESSION_SUMMARY_NAME = "session.json"
_REMOTE_SESSION_REGISTRY_DIRNAME = "_sessions"
_REMOTE_SESSION_LEASE_INTERVAL_S = 1.0
_REMOTE_SESSION_LEASE_TIMEOUT_S = 5.0


@dataclass(slots=True)
class _ManagedRemoteSession:
    session_id: str
    source_path: Path
    output_root: Path
    submitted_at: datetime
    status: RemoteSessionState = "queued"
    completed_at: datetime | None = None
    simulation_input_path: Path | None = None
    simulation: SimulationRun | None = None
    bundle_path: Path | None = None
    dry_run: bool = False
    error: str | None = None
    owner_host_id: str | None = None
    owner_instance_id: str | None = None
    owner_pid: int | None = None
    lease_heartbeat_at: datetime | None = None
    thread: Thread | None = None
    lease_thread: Thread | None = None
    lease_stop: Event = field(default_factory=Event)
    lock: Lock = field(default_factory=Lock)


def _validate_session_id(session_id: str) -> str:
    normalized = session_id.strip()
    if fullmatch(_REMOTE_SESSION_ID_PATTERN, normalized) is None:
        raise ValidationError(
            "session_id must match the generated remote session identifier format."
        )
    return normalized


def _remote_registry_root(*, workspace_root: Path) -> Path:
    return (workspace_root / "artifacts" / "remote" / _REMOTE_SESSION_REGISTRY_DIRNAME).resolve(
        strict=False
    )


def _remote_registry_path(session_id: str, *, workspace_root: Path) -> Path:
    return (_remote_registry_root(workspace_root=workspace_root) / f"{session_id}.json").resolve(
        strict=False
    )


def _remote_summary_path(output_root: Path) -> Path:
    return (output_root / _REMOTE_SESSION_SUMMARY_NAME).resolve(strict=False)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _current_host_id() -> str:
    host_id = socket.gethostname().strip().lower()
    return host_id or "unknown-host"


def _serialize_simulation(simulation: SimulationRun | None) -> dict[str, object] | None:
    if simulation is None:
        return None
    return {
        "adapter_key": simulation.adapter_key,
        "command": list(simulation.command),
        "working_directory": str(simulation.working_directory),
        "netlist_path": str(simulation.netlist_path),
        "log_path": str(simulation.log_path),
        "raw_path": str(simulation.raw_path),
        "dry_run": simulation.dry_run,
        "started_at": simulation.started_at.isoformat(),
        "exit_code": simulation.exit_code,
        "duration_s": simulation.duration_s,
        "stdout": simulation.stdout,
        "stderr": simulation.stderr,
        "log_exists": simulation.log_exists,
        "raw_exists": simulation.raw_exists,
    }


def _serialize_session(session: _ManagedRemoteSession) -> dict[str, object]:
    return stamp_schema_version(
        {
            "session_id": session.session_id,
            "status": session.status,
            "source_path": str(session.source_path),
            "output_root": str(session.output_root),
            "submitted_at": session.submitted_at.isoformat(),
            "completed_at": None
            if session.completed_at is None
            else session.completed_at.isoformat(),
            "simulation_input_path": None
            if session.simulation_input_path is None
            else str(session.simulation_input_path),
            "bundle_path": None if session.bundle_path is None else str(session.bundle_path),
            "dry_run": session.dry_run,
            "error": session.error,
            "owner_host_id": session.owner_host_id,
            "owner_instance_id": session.owner_instance_id,
            "owner_pid": session.owner_pid,
            "lease_heartbeat_at": None
            if session.lease_heartbeat_at is None
            else session.lease_heartbeat_at.isoformat(),
            "simulation": _serialize_simulation(session.simulation),
        }
    )


def _ensure_new_remote_output_root(output_root: Path) -> None:
    if output_root.exists() and not output_root.is_dir():
        raise ValidationError("Remote session output_root must resolve to a directory path.")
    if output_root.is_dir() and any(output_root.iterdir()):
        raise ValidationError(
            "Remote session output_root must be empty so sessions remain execution-isolated."
        )


def _deserialize_simulation(
    payload: object,
    *,
    workspace_root: Path,
) -> SimulationRun | None:
    if not isinstance(payload, dict):
        return None
    return SimulationRun(
        adapter_key=str(payload.get("adapter_key", "")),
        command=tuple(str(item) for item in payload.get("command", ())),
        working_directory=resolve_workspace_path(
            str(payload["working_directory"]), workspace_root=workspace_root
        ),
        netlist_path=resolve_workspace_path(
            str(payload["netlist_path"]), workspace_root=workspace_root
        ),
        log_path=resolve_workspace_path(str(payload["log_path"]), workspace_root=workspace_root),
        raw_path=resolve_workspace_path(str(payload["raw_path"]), workspace_root=workspace_root),
        dry_run=bool(payload.get("dry_run", False)),
        started_at=_parse_datetime(payload.get("started_at")) or datetime.now().astimezone(),
        exit_code=None if payload.get("exit_code") is None else int(payload["exit_code"]),
        duration_s=None if payload.get("duration_s") is None else float(payload["duration_s"]),
        stdout=str(payload.get("stdout", "")),
        stderr=str(payload.get("stderr", "")),
        log_exists=bool(payload.get("log_exists", False)),
        raw_exists=bool(payload.get("raw_exists", False)),
    )


def _resolve_remote_output_root(
    source_path: Path,
    *,
    workspace_root: Path,
    session_id: str,
    output_dir: str | None,
) -> Path:
    if output_dir is not None:
        return resolve_workspace_path(output_dir, workspace_root=workspace_root)
    return (
        workspace_root / "artifacts" / "remote" / f"{slugify(source_path.stem)}-{session_id}"
    ).resolve(strict=False)


def _normalize_artifact_kinds(
    artifact_kinds: tuple[str, ...] | list[str] | None,
) -> tuple[RemoteArtifactKind, ...]:
    if artifact_kinds is None:
        return _DEFAULT_ARTIFACT_KINDS
    normalized = tuple(kind.strip().lower() for kind in artifact_kinds)
    if not normalized:
        raise ValueError("artifact_kinds must contain at least one entry when provided.")
    for kind in normalized:
        if kind not in _VALID_ARTIFACT_KINDS:
            choices = ", ".join(sorted(_VALID_ARTIFACT_KINDS))
            raise ValueError(f"artifact_kinds entries must be one of: {choices}.")
    return tuple(cast("RemoteArtifactKind", kind) for kind in normalized)


class RemoteSimulationManager:
    """Manage remote-style single-run execution and zipped artifact transport."""

    def __init__(self, settings: QSpiceSettings) -> None:
        self.settings = settings.normalized()
        self._sessions: dict[str, _ManagedRemoteSession] = {}
        self._manager_host_id = _current_host_id()
        self._manager_instance_id = f"remote-manager-{uuid4().hex[:12]}"

    def _touch_session_lease(self, session: _ManagedRemoteSession) -> None:
        session.owner_host_id = self._manager_host_id
        session.owner_instance_id = self._manager_instance_id
        session.owner_pid = os.getpid()
        session.lease_heartbeat_at = datetime.now().astimezone()

    def _mark_session_orphaned(self, session: _ManagedRemoteSession, *, reason: str) -> None:
        with session.lock:
            if session.status not in {"queued", "running"} or session.thread is not None:
                return
            session.status = "failed"
            session.error = reason
            session.completed_at = datetime.now().astimezone()
            session.owner_instance_id = None
            session.owner_pid = None
            session.lease_heartbeat_at = None
            self._persist_session(session)

    def _lease_is_fresh(self, heartbeat: datetime | None) -> bool:
        if heartbeat is None:
            return False
        age_s = (datetime.now().astimezone() - heartbeat).total_seconds()
        return age_s <= _REMOTE_SESSION_LEASE_TIMEOUT_S

    def _start_session_lease_thread(self, session: _ManagedRemoteSession) -> None:
        session.lease_stop.clear()

        def keep_lease_alive() -> None:
            while not session.lease_stop.wait(_REMOTE_SESSION_LEASE_INTERVAL_S):
                with session.lock:
                    if session.status not in {"queued", "running"}:
                        return
                    if session.owner_instance_id != self._manager_instance_id:
                        return
                    self._touch_session_lease(session)
                    self._persist_session(session)

        lease_thread = Thread(
            target=keep_lease_alive,
            name=f"{session.session_id}-lease",
            daemon=True,
        )
        session.lease_thread = lease_thread
        lease_thread.start()

    def _stop_session_lease(self, session: _ManagedRemoteSession) -> None:
        session.lease_stop.set()

    def _maybe_mark_orphaned_session(self, session: _ManagedRemoteSession) -> None:
        if session.thread is not None or session.status not in {"queued", "running"}:
            return
        if session.owner_host_id not in {None, self._manager_host_id}:
            if self._lease_is_fresh(session.lease_heartbeat_at):
                return
            self._mark_session_orphaned(
                session,
                reason=(
                    "Remote session was orphaned before completion because its owning host "
                    f"{session.owner_host_id} stopped refreshing its lease."
                ),
            )
            return
        owner_pid = session.owner_pid
        owner_alive = owner_pid is not None and _pid_exists(owner_pid)
        if owner_alive and self._lease_is_fresh(session.lease_heartbeat_at):
            return
        self._mark_session_orphaned(
            session,
            reason=(
                "Remote session was orphaned before completion because its owning "
                "manager process stopped or its lease expired."
            ),
        )

    def _persist_session(self, session: _ManagedRemoteSession) -> None:
        payload = _serialize_session(session)
        summary_path = _remote_summary_path(session.output_root)
        registry_path = _remote_registry_path(
            session.session_id,
            workspace_root=self.settings.workspace_root,
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        summary_text = json.dumps(payload, indent=2)
        summary_path.write_text(summary_text, encoding="utf-8")
        registry_path.write_text(summary_text, encoding="utf-8")

    def _load_persisted_session(self, session_id: str) -> _ManagedRemoteSession:
        validated_id = _validate_session_id(session_id)
        registry_path = validate_existing_file(
            _remote_registry_path(validated_id, workspace_root=self.settings.workspace_root),
            workspace_root=self.settings.workspace_root,
            suffixes=(".json",),
        )
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        validate_schema_version(
            payload,
            artifact_name="Remote session summary",
            allow_legacy_unversioned=False,
        )
        output_root = resolve_workspace_path(
            str(payload["output_root"]),
            workspace_root=self.settings.workspace_root,
        )
        return _ManagedRemoteSession(
            session_id=str(payload["session_id"]),
            source_path=resolve_workspace_path(
                str(payload["source_path"]), workspace_root=self.settings.workspace_root
            ),
            output_root=output_root,
            submitted_at=(
                _parse_datetime(payload.get("submitted_at")) or datetime.now().astimezone()
            ),
            status=cast("RemoteSessionState", str(payload.get("status", "failed"))),
            completed_at=_parse_datetime(payload.get("completed_at")),
            simulation_input_path=(
                None
                if payload.get("simulation_input_path") is None
                else resolve_workspace_path(
                    str(payload["simulation_input_path"]),
                    workspace_root=self.settings.workspace_root,
                )
            ),
            simulation=_deserialize_simulation(
                payload.get("simulation"),
                workspace_root=self.settings.workspace_root,
            ),
            bundle_path=(
                None
                if payload.get("bundle_path") is None
                else resolve_workspace_path(
                    str(payload["bundle_path"]),
                    workspace_root=self.settings.workspace_root,
                )
            ),
            dry_run=bool(payload.get("dry_run", False)),
            error=None if payload.get("error") is None else str(payload["error"]),
            owner_host_id=(
                None if payload.get("owner_host_id") is None else str(payload["owner_host_id"])
            ),
            owner_instance_id=(
                None
                if payload.get("owner_instance_id") is None
                else str(payload["owner_instance_id"])
            ),
            owner_pid=(None if payload.get("owner_pid") is None else int(payload["owner_pid"])),
            lease_heartbeat_at=_parse_datetime(payload.get("lease_heartbeat_at")),
        )

    def _require_session(self, session_id: str) -> _ManagedRemoteSession:
        validated_id = _validate_session_id(session_id)
        session = self._sessions.get(validated_id)
        if session is not None:
            self._maybe_mark_orphaned_session(session)
            return session
        loaded = self._load_persisted_session(validated_id)
        self._sessions[validated_id] = loaded
        self._maybe_mark_orphaned_session(loaded)
        return loaded

    def submit_remote_simulation(
        self,
        *,
        source_path: str,
        output_dir: str | None = None,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
    ) -> RemoteSimulationSubmission:
        resolved_source = validate_existing_file(
            source_path,
            workspace_root=self.settings.workspace_root,
            suffixes=(".qsch", ".net", ".cir"),
        )
        session_id = f"remote-{uuid4().hex[:12]}"
        output_root = _resolve_remote_output_root(
            resolved_source,
            workspace_root=self.settings.workspace_root,
            session_id=session_id,
            output_dir=output_dir,
        )
        _ensure_new_remote_output_root(output_root)
        submitted_at = datetime.now().astimezone()
        session = _ManagedRemoteSession(
            session_id=session_id,
            source_path=resolved_source,
            output_root=output_root,
            submitted_at=submitted_at,
            dry_run=dry_run,
        )
        self._touch_session_lease(session)
        output_root.mkdir(parents=True, exist_ok=True)
        self._sessions[session_id] = session
        self._persist_session(session)
        logger = get_logger(component="services.remote_manager", session_id=session_id)
        logger.info("remote_session_submitted", dry_run=dry_run)
        captured_context = copy_context()

        def run_session() -> None:
            captured_context.run(
                self._run_remote_session,
                session=session,
                timeout_s=timeout_s,
                ascii_raw=ascii_raw,
                extra_switches=tuple(extra_switches or ()),
            )

        thread = Thread(
            target=run_session,
            name=session_id,
            daemon=True,
        )
        session.thread = thread
        self._start_session_lease_thread(session)
        thread.start()

        return RemoteSimulationSubmission(
            session_id=session_id,
            status="queued",
            source_path=resolved_source,
            output_root=output_root,
            submitted_at=submitted_at,
            owner_host_id=session.owner_host_id or self._manager_host_id,
        )

    def poll_remote_run(self, session_id: str) -> RemoteRunStatus:
        session = self._require_session(session_id)
        with session.lock:
            simulation = session.simulation
            log_path = None if simulation is None else simulation.log_path
            raw_path = None if simulation is None else simulation.raw_path
            bundle_path = session.bundle_path
            return RemoteRunStatus(
                session_id=session.session_id,
                status=session.status,
                source_path=session.source_path,
                output_root=session.output_root,
                submitted_at=session.submitted_at,
                completed_at=session.completed_at,
                simulation_input_path=session.simulation_input_path,
                log_path=log_path,
                raw_path=raw_path,
                bundle_path=bundle_path,
                dry_run=session.dry_run,
                exit_code=None if simulation is None else simulation.exit_code,
                duration_s=None if simulation is None else simulation.duration_s,
                log_available=bool(log_path and log_path.is_file()),
                raw_available=bool(raw_path and raw_path.is_file()),
                bundle_available=bool(bundle_path and bundle_path.is_file()),
                owner_host_id=session.owner_host_id,
                lease_heartbeat_at=session.lease_heartbeat_at,
                error=session.error,
            )

    def download_remote_artifacts(
        self,
        session_id: str,
        *,
        output_path: str | Path | None = None,
        artifact_kinds: tuple[str, ...] | list[str] | None = None,
    ) -> RemoteArtifactDownload:
        session = self._require_session(session_id)
        with session.lock:
            if session.status in {"queued", "running"}:
                raise ValueError("Remote session is still active; artifacts are not ready yet.")
            selected_kinds = _normalize_artifact_kinds(artifact_kinds)
            simulation = session.simulation
            destination = resolve_workspace_output_path(
                output_path,
                workspace_root=self.settings.workspace_root,
                default=session.output_root / f"{session.source_path.stem}-remote-artifacts.zip",
                suffixes=(".zip",),
            )
            destination.parent.mkdir(parents=True, exist_ok=True)

            summary_payload = _serialize_session(session)

            entry_names: list[str] = []
            with ZipFile(destination, mode="w", compression=ZIP_DEFLATED) as archive:
                if "summary" in selected_kinds:
                    archive.writestr("session.json", json.dumps(summary_payload, indent=2))
                    entry_names.append("session.json")
                if "source" in selected_kinds and session.source_path.is_file():
                    archive.write(
                        session.source_path,
                        arcname=f"source/{session.source_path.name}",
                    )
                    entry_names.append(f"source/{session.source_path.name}")
                if simulation is not None:
                    if "netlist" in selected_kinds and simulation.netlist_path.is_file():
                        archive.write(
                            simulation.netlist_path,
                            arcname=f"netlist/{simulation.netlist_path.name}",
                        )
                        entry_names.append(f"netlist/{simulation.netlist_path.name}")
                    if "log" in selected_kinds and simulation.log_path.is_file():
                        archive.write(
                            simulation.log_path,
                            arcname=f"artifacts/{simulation.log_path.name}",
                        )
                        entry_names.append(f"artifacts/{simulation.log_path.name}")
                    if "raw" in selected_kinds and simulation.raw_path.is_file():
                        archive.write(
                            simulation.raw_path,
                            arcname=f"artifacts/{simulation.raw_path.name}",
                        )
                        entry_names.append(f"artifacts/{simulation.raw_path.name}")
            if not entry_names:
                raise ValueError("No selected remote artifacts were available for download.")
            session.bundle_path = destination
            self._persist_session(session)

            return RemoteArtifactDownload(
                session_id=session.session_id,
                status=session.status,
                output_path=destination,
                artifact_kinds=selected_kinds,
                entry_names=tuple(entry_names),
                artifact_count=len(entry_names),
                bundle_size_bytes=destination.stat().st_size,
            )

    def close_remote_session(
        self,
        session_id: str,
        *,
        delete_bundle: bool = False,
    ) -> RemoteSessionClosure:
        session = self._require_session(session_id)
        with session.lock:
            if session.status in {"queued", "running"}:
                raise ValueError("Remote session is still active and cannot be closed yet.")
            bundle_deleted = False
            if delete_bundle and session.bundle_path is not None and session.bundle_path.is_file():
                session.bundle_path.unlink()
                session.bundle_path = None
                bundle_deleted = True
            session.status = "closed"
            self._persist_session(session)
            return RemoteSessionClosure(
                session_id=session.session_id,
                status=session.status,
                output_root=session.output_root,
                bundle_deleted=bundle_deleted,
                note=(
                    "Remote session closed. Generated artifacts remain in the workspace."
                    if not bundle_deleted
                    else "Remote session closed and the staged download bundle was deleted."
                ),
            )

    def _run_remote_session(
        self,
        *,
        session: _ManagedRemoteSession,
        timeout_s: float | None,
        ascii_raw: bool,
        extra_switches: tuple[str, ...],
    ) -> None:
        logger = get_logger(component="services.remote_manager", session_id=session.session_id)
        with session.lock:
            session.status = "running"
            self._touch_session_lease(session)
            self._persist_session(session)

        logger.info("remote_session_execution_started", dry_run=session.dry_run)
        try:
            with operation_span(
                "remote.execute",
                enabled=self.settings.telemetry_enabled,
                attributes={
                    "qspice.session_id": session.session_id,
                    "qspice.dry_run": session.dry_run,
                },
            ):
                session.output_root.mkdir(parents=True, exist_ok=True)
                if session.source_path.suffix.lower() == ".qsch":
                    netlist_output = (
                        session.output_root / session.source_path.with_suffix(".net").name
                    )
                    generated = generate_netlist(
                        session.source_path,
                        workspace_root=self.settings.workspace_root,
                        output_path=netlist_output,
                        settings=self.settings,
                    )
                    simulation_input = generated.netlist_path
                else:
                    staged_input = (session.output_root / session.source_path.name).resolve(
                        strict=False
                    )
                    if staged_input != session.source_path:
                        shutil.copy2(session.source_path, staged_input)
                    simulation_input = staged_input

                log_path = session.output_root / session.source_path.with_suffix(".log").name
                raw_path = session.output_root / session.source_path.with_suffix(".qraw").name

                with session.lock:
                    session.simulation_input_path = simulation_input
                    self._persist_session(session)

                simulation = run_simulation(
                    simulation_input,
                    workspace_root=self.settings.workspace_root,
                    settings=self.settings,
                    dry_run=session.dry_run,
                    timeout_s=timeout_s,
                    log_path=log_path,
                    raw_output_path=raw_path,
                    extra_switches=extra_switches,
                    ascii_raw=ascii_raw,
                )
        except Exception as exc:
            logger.exception("remote_session_execution_failed")
            with session.lock:
                session.status = "failed"
                session.error = str(exc)
                session.completed_at = datetime.now().astimezone()
                session.thread = None
                self._stop_session_lease(session)
                self._persist_session(session)
            return

        with session.lock:
            session.simulation_input_path = simulation_input
            session.simulation = simulation
            session.status = "completed"
            session.completed_at = datetime.now().astimezone()
            session.thread = None
            self._stop_session_lease(session)
            self._persist_session(session)
        logger.info("remote_session_execution_completed", exit_code=simulation.exit_code)


__all__ = ["RemoteArtifactKind", "RemoteSessionState", "RemoteSimulationManager"]
