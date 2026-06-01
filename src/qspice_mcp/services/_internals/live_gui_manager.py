"""Persisted live GUI bridge session lifecycle management."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from re import fullmatch
from shutil import which
from typing import TYPE_CHECKING, Literal, cast
from uuid import uuid4

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.infra.logging import get_logger
from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._internals.simulation_batch import slugify
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.live_gui.close_live_gui_session import LiveGuiSessionClosure
from qspice_mcp.services.live_gui.launch_live_gui_session import LiveGuiSessionLaunch
from qspice_mcp.services.live_gui.poll_live_gui_session import LiveGuiSessionStatus
from qspice_mcp.services.live_gui.poll_live_gui_session_events import (
    LiveGuiSessionEvent,
    LiveGuiSessionEventPoll,
)
from qspice_mcp.services.live_gui.scaffold_live_gui_session import scaffold_live_gui_session
from qspice_mcp.services.live_gui.send_live_gui_session_command import (
    LiveGuiSessionCommandDispatch,
)

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings

LiveGuiSessionState = Literal["queued", "running", "completed", "failed", "closed"]

_LIVE_GUI_SESSION_ID_PATTERN = r"livegui-[0-9a-f]{12}"
_LIVE_GUI_REGISTRY_DIRNAME = "_sessions"
_LIVE_GUI_SUMMARY_NAME = "session.json"
_LIVE_GUI_COMMAND_QUEUE_NAME = "bridge.commands.jsonl"
_LIVE_GUI_EVENT_LOG_NAME = "bridge.events.jsonl"


@dataclass(slots=True)
class _ManagedLiveGuiSession:
    session_id: str
    session_name: str
    manifest_path: Path
    output_root: Path
    bridge_command: tuple[str, ...]
    submitted_at: datetime
    stdout_path: Path
    stderr_path: Path
    status: LiveGuiSessionState = "queued"
    completed_at: datetime | None = None
    bridge_pid: int | None = None
    bridge_exit_code: int | None = None
    error: str | None = None
    process: subprocess.Popen[bytes] | None = None


def _validate_session_id(session_id: str) -> str:
    normalized = session_id.strip()
    if fullmatch(_LIVE_GUI_SESSION_ID_PATTERN, normalized) is None:
        raise ValidationError(
            "session_id must match the generated live GUI session identifier format."
        )
    return normalized


def _live_gui_registry_root(*, workspace_root: Path) -> Path:
    return (workspace_root / "artifacts" / "live_gui" / _LIVE_GUI_REGISTRY_DIRNAME).resolve(
        strict=False
    )


def _live_gui_registry_path(session_id: str, *, workspace_root: Path) -> Path:
    return (_live_gui_registry_root(workspace_root=workspace_root) / f"{session_id}.json").resolve(
        strict=False
    )


def _live_gui_summary_path(output_root: Path) -> Path:
    return (output_root / _LIVE_GUI_SUMMARY_NAME).resolve(strict=False)


def _live_gui_command_queue_path(output_root: Path) -> Path:
    return (output_root / _LIVE_GUI_COMMAND_QUEUE_NAME).resolve(strict=False)


def _live_gui_event_log_path(output_root: Path) -> Path:
    return (output_root / _LIVE_GUI_EVENT_LOG_NAME).resolve(strict=False)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)


def _touch_jsonl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _append_jsonl_record(path: Path, payload: dict[str, object]) -> None:
    _touch_jsonl(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _read_jsonl_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValidationError("Live GUI bridge event files must contain JSON object lines.")
        records.append({str(key): value for key, value in payload.items()})
    return records


def _serialize_session(session: _ManagedLiveGuiSession) -> dict[str, object]:
    return stamp_schema_version(
        {
            "session_id": session.session_id,
            "session_name": session.session_name,
            "manifest_path": str(session.manifest_path),
            "output_root": str(session.output_root),
            "bridge_command": list(session.bridge_command),
            "submitted_at": session.submitted_at.isoformat(),
            "completed_at": None
            if session.completed_at is None
            else session.completed_at.isoformat(),
            "stdout_path": str(session.stdout_path),
            "stderr_path": str(session.stderr_path),
            "status": session.status,
            "bridge_pid": session.bridge_pid,
            "bridge_exit_code": session.bridge_exit_code,
            "error": session.error,
        }
    )


def _ensure_new_live_gui_output_root(output_root: Path) -> None:
    if output_root.exists() and not output_root.is_dir():
        raise ValidationError("Live GUI output_root must resolve to a directory path.")
    if output_root.is_dir() and any(output_root.iterdir()):
        raise ValidationError(
            "Live GUI output_root must be empty so bridge sessions remain execution-isolated."
        )


def _resolve_bridge_command(settings: QSpiceSettings) -> tuple[str, ...]:
    normalized = settings.normalized().live_gui_bridge_command
    if not normalized:
        raise BackendUnavailableError(
            "No live GUI bridge command is configured for Windows-message runtime launch."
        )
    executable = normalized[0]
    candidate = Path(executable)
    if candidate.is_file():
        resolved_executable = str(candidate.resolve(strict=False))
    else:
        resolved_executable = which(executable) or ""
    if not resolved_executable:
        raise BackendUnavailableError(
            "The configured live GUI bridge command does not resolve to an executable."
        )
    return (resolved_executable, *normalized[1:])


class LiveGuiSessionManager:
    """Manage launched live GUI bridge sessions and persisted status snapshots."""

    def __init__(self, settings: QSpiceSettings) -> None:
        self.settings = settings.normalized()
        self._sessions: dict[str, _ManagedLiveGuiSession] = {}

    def _persist_session(self, session: _ManagedLiveGuiSession) -> None:
        payload = _serialize_session(session)
        summary_path = _live_gui_summary_path(session.output_root)
        registry_path = _live_gui_registry_path(
            session.session_id,
            workspace_root=self.settings.workspace_root,
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        summary_text = json.dumps(payload, indent=2)
        summary_path.write_text(summary_text, encoding="utf-8")
        registry_path.write_text(summary_text, encoding="utf-8")

    def _load_persisted_session(self, session_id: str) -> _ManagedLiveGuiSession:
        validated_id = _validate_session_id(session_id)
        registry_path = validate_existing_file(
            _live_gui_registry_path(validated_id, workspace_root=self.settings.workspace_root),
            workspace_root=self.settings.workspace_root,
            suffixes=(".json",),
        )
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        validate_schema_version(
            payload,
            artifact_name="Live GUI session summary",
            allow_legacy_unversioned=False,
        )
        return _ManagedLiveGuiSession(
            session_id=str(payload["session_id"]),
            session_name=str(payload.get("session_name") or validated_id),
            manifest_path=resolve_workspace_path(
                str(payload["manifest_path"]),
                workspace_root=self.settings.workspace_root,
            ),
            output_root=resolve_workspace_path(
                str(payload["output_root"]),
                workspace_root=self.settings.workspace_root,
            ),
            bridge_command=tuple(str(item) for item in payload.get("bridge_command", ())),
            submitted_at=_parse_datetime(payload.get("submitted_at"))
            or datetime.now().astimezone(),
            completed_at=_parse_datetime(payload.get("completed_at")),
            stdout_path=resolve_workspace_path(
                str(payload["stdout_path"]),
                workspace_root=self.settings.workspace_root,
            ),
            stderr_path=resolve_workspace_path(
                str(payload["stderr_path"]),
                workspace_root=self.settings.workspace_root,
            ),
            status=cast("LiveGuiSessionState", str(payload.get("status", "failed"))),
            bridge_pid=(None if payload.get("bridge_pid") is None else int(payload["bridge_pid"])),
            bridge_exit_code=(
                None
                if payload.get("bridge_exit_code") is None
                else int(payload["bridge_exit_code"])
            ),
            error=None if payload.get("error") is None else str(payload["error"]),
        )

    def _require_session(self, session_id: str) -> _ManagedLiveGuiSession:
        validated_id = _validate_session_id(session_id)
        session = self._sessions.get(validated_id)
        if session is not None:
            return session
        loaded = self._load_persisted_session(validated_id)
        self._sessions[validated_id] = loaded
        return loaded

    def _refresh_session(self, session: _ManagedLiveGuiSession) -> None:
        if session.process is None:
            return
        exit_code = session.process.poll()
        if exit_code is None:
            session.status = "running"
            session.bridge_pid = session.process.pid
            return
        session.bridge_pid = None
        session.bridge_exit_code = exit_code
        session.completed_at = datetime.now().astimezone()
        session.process = None
        if session.status == "closed":
            return
        if exit_code == 0:
            session.status = "completed"
        else:
            session.status = "failed"
            session.error = f"Live GUI bridge exited with status {exit_code}."
        self._persist_session(session)

    def launch_live_gui_session(
        self,
        *,
        session_name: str,
        schematic_path: str | Path | None = None,
        waveform_names: list[str] | tuple[str, ...] | None = None,
        cross_probe_signals: list[str] | tuple[str, ...] | None = None,
        output_path: str | Path | None = None,
    ) -> LiveGuiSessionLaunch:
        if sys.platform != "win32":
            raise BackendUnavailableError(
                "Live GUI bridge execution is currently supported only on Windows hosts."
            )
        bridge_command_prefix = _resolve_bridge_command(self.settings)
        session_id = f"livegui-{uuid4().hex[:12]}"
        output_root = (
            self.settings.workspace_root
            / "artifacts"
            / "live_gui"
            / f"{slugify(session_name)}-{session_id}"
        ).resolve(strict=False)
        _ensure_new_live_gui_output_root(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        manifest_path = (
            resolve_workspace_path(output_path, workspace_root=self.settings.workspace_root)
            if output_path is not None
            else (output_root / "manifest.json").resolve(strict=False)
        )
        if output_path is not None:
            _ensure_new_live_gui_output_root(manifest_path.parent.resolve(strict=False))
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            output_root = manifest_path.parent.resolve(strict=False)

        scaffold = scaffold_live_gui_session(
            session_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            schematic_path=schematic_path,
            waveform_names=waveform_names,
            cross_probe_signals=cross_probe_signals,
            output_path=manifest_path,
        )
        submitted_at = datetime.now().astimezone()
        stdout_path = (output_root / "bridge.stdout.log").resolve(strict=False)
        stderr_path = (output_root / "bridge.stderr.log").resolve(strict=False)
        _touch_jsonl(_live_gui_command_queue_path(output_root))
        _touch_jsonl(_live_gui_event_log_path(output_root))
        bridge_command = (*bridge_command_prefix, str(scaffold.manifest_path))
        logger = get_logger(component="services.live_gui_manager", session_id=session_id)

        with (
            stdout_path.open("w", encoding="utf-8") as stdout_stream,
            stderr_path.open("w", encoding="utf-8") as stderr_stream,
        ):
            process = subprocess.Popen(  # noqa: S603
                bridge_command,
                cwd=str(self.settings.workspace_root),
                stdout=stdout_stream,
                stderr=stderr_stream,
            )

        session = _ManagedLiveGuiSession(
            session_id=session_id,
            session_name=session_name.strip(),
            manifest_path=scaffold.manifest_path,
            output_root=output_root,
            bridge_command=bridge_command,
            submitted_at=submitted_at,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            status="running",
            bridge_pid=process.pid,
            process=process,
        )
        self._sessions[session_id] = session
        self._persist_session(session)
        logger.info("live_gui_session_launched", bridge_pid=process.pid)
        return LiveGuiSessionLaunch(
            session_id=session.session_id,
            session_name=session.session_name,
            status=session.status,
            manifest_path=session.manifest_path,
            output_root=session.output_root,
            bridge_command=session.bridge_command,
            submitted_at=session.submitted_at,
            bridge_pid=session.bridge_pid,
            notes=(*scaffold.notes, "The configured live GUI bridge command was launched."),
        )

    def poll_live_gui_session(self, session_id: str) -> LiveGuiSessionStatus:
        session = self._require_session(session_id)
        self._refresh_session(session)
        duration_s = None
        if session.completed_at is not None:
            duration_s = (session.completed_at - session.submitted_at).total_seconds()
        live_process_attached = session.process is not None
        notes: list[str] = []
        if not live_process_attached and session.status in {"queued", "running"}:
            notes.append(
                "This manager instance does not hold a live bridge handle for the "
                "persisted session."
            )
        if session.error is not None:
            notes.append(session.error)
        return LiveGuiSessionStatus(
            session_id=session.session_id,
            session_name=session.session_name,
            status=session.status,
            manifest_path=session.manifest_path,
            output_root=session.output_root,
            bridge_command=session.bridge_command,
            submitted_at=session.submitted_at,
            completed_at=session.completed_at,
            bridge_pid=session.bridge_pid,
            bridge_exit_code=session.bridge_exit_code,
            duration_s=duration_s,
            live_process_attached=live_process_attached,
            stdout_path=session.stdout_path,
            stderr_path=session.stderr_path,
            error=session.error,
            notes=tuple(notes),
        )

    def send_live_gui_session_command(
        self,
        session_id: str,
        *,
        command: str,
        signal: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> LiveGuiSessionCommandDispatch:
        session = self._require_session(session_id)
        self._refresh_session(session)
        normalized_command = command.strip()
        if not normalized_command:
            raise ValidationError("command must not be empty.")
        if session.status in {"completed", "failed", "closed"}:
            raise ValidationError("Cannot send commands to a terminal live GUI session.")
        normalized_signal = None if signal is None else signal.strip()
        if signal is not None and not normalized_signal:
            raise ValidationError("signal must not be empty when provided.")
        command_path = _live_gui_command_queue_path(session.output_root)
        command_id = len(_read_jsonl_records(command_path)) + 1
        queued_at = datetime.now().astimezone()
        normalized_payload = {} if payload is None else dict(payload)
        _append_jsonl_record(
            command_path,
            {
                "command_id": command_id,
                "session_id": session.session_id,
                "command": normalized_command,
                "signal": normalized_signal,
                "payload": normalized_payload,
                "queued_at": queued_at.isoformat(),
            },
        )
        return LiveGuiSessionCommandDispatch(
            session_id=session.session_id,
            command_id=command_id,
            command=normalized_command,
            signal=normalized_signal,
            payload=normalized_payload,
            queued_at=queued_at,
            command_path=command_path,
            note="Queued a bridge command for live GUI message translation.",
        )

    def poll_live_gui_session_events(
        self,
        session_id: str,
        *,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> LiveGuiSessionEventPoll:
        if after_sequence < 0:
            raise ValidationError("after_sequence must be greater than or equal to zero.")
        if limit <= 0:
            raise ValidationError("limit must be greater than zero.")
        session = self._require_session(session_id)
        self._refresh_session(session)
        event_path = _live_gui_event_log_path(session.output_root)
        _touch_jsonl(event_path)
        events: list[LiveGuiSessionEvent] = []
        next_sequence = after_sequence
        for record in _read_jsonl_records(event_path):
            sequence_value = record.get("sequence", 0)
            if not isinstance(sequence_value, int | str):
                raise ValidationError("Live GUI bridge events must provide an integer sequence.")
            sequence = int(sequence_value)
            if sequence <= after_sequence:
                continue
            payload_value = record.get("payload")
            events.append(
                LiveGuiSessionEvent(
                    sequence=sequence,
                    event=str(record.get("event", "unknown")),
                    created_at=_parse_datetime(record.get("created_at")),
                    signal=None if record.get("signal") is None else str(record["signal"]),
                    payload=(
                        {}
                        if not isinstance(payload_value, dict)
                        else {str(key): value for key, value in payload_value.items()}
                    ),
                )
            )
            next_sequence = sequence
            if len(events) >= limit:
                break
        notes: list[str] = []
        if not events:
            notes.append("No new bridge events were recorded for this session.")
        return LiveGuiSessionEventPoll(
            session_id=session.session_id,
            status=session.status,
            event_path=event_path,
            next_sequence=next_sequence,
            events=tuple(events),
            live_process_attached=session.process is not None,
            notes=tuple(notes),
        )

    def close_live_gui_session(
        self,
        session_id: str,
        *,
        delete_manifest: bool = False,
    ) -> LiveGuiSessionClosure:
        session = self._require_session(session_id)
        self._refresh_session(session)
        bridge_terminated = False
        if session.process is not None and session.process.poll() is None:
            session.process.terminate()
            try:
                session.bridge_exit_code = session.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                session.process.kill()
                session.bridge_exit_code = session.process.wait(timeout=5)
            bridge_terminated = True
            session.process = None
            session.bridge_pid = None
            session.completed_at = datetime.now().astimezone()
        manifest_deleted = False
        if delete_manifest and session.manifest_path.exists():
            session.manifest_path.unlink()
            manifest_deleted = True
        session.status = "closed"
        self._persist_session(session)
        return LiveGuiSessionClosure(
            session_id=session.session_id,
            status=session.status,
            output_root=session.output_root,
            manifest_path=session.manifest_path,
            bridge_terminated=bridge_terminated,
            manifest_deleted=manifest_deleted,
            note="Closed live GUI session.",
        )


__all__ = ["LiveGuiSessionManager"]
