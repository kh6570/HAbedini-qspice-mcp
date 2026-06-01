"""In-memory background batch execution manager."""

from __future__ import annotations

import json
from contextvars import copy_context
from dataclasses import dataclass, field
from datetime import datetime
from re import fullmatch
from threading import Lock, Thread
from typing import TYPE_CHECKING, cast
from uuid import uuid4

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra.logging import get_logger
from qspice_mcp.infra.telemetry import operation_span
from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._internals.simulation_batch import (
    BatchState,
    RetainedArtifactPolicy,
    SimulationBatch,
    SweepKind,
    batch_manifest_path,
    load_batch_manifest,
    resolve_sweep_output_root,
)
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.batch.cancel_batch import BatchCancellation
from qspice_mcp.services.batch.collect_batch_results import BatchCollection
from qspice_mcp.services.batch.get_batch_status import BatchStatus
from qspice_mcp.services.batch.submit_batch import BatchSubmission
from qspice_mcp.services.simulation.run_model_sweep import run_model_sweep
from qspice_mcp.services.simulation.run_param_sweep import run_param_sweep
from qspice_mcp.services.simulation.run_value_sweep import run_value_sweep

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(slots=True)
class _ManagedBatchRequest:
    reference: str | None = None
    values: list[str | int | float] | None = None
    parameters: dict[str, list[str | int | float | bool]] | None = None
    models: list[str] | None = None
    parallelism: int = 1
    dry_run: bool = False
    timeout_s: float | None = None
    ascii_raw: bool = False
    extra_switches: tuple[str, ...] = ()
    resume: bool = False
    retained_artifact_policy: RetainedArtifactPolicy = "cleanup"


@dataclass(slots=True)
class _ManagedBatch:
    batch_id: str
    batch_kind: SweepKind
    source_path: Path
    output_root: Path
    manifest_path: Path
    submitted_at: datetime
    status: BatchState = "queued"
    completed_run_count: int = 0
    run_count: int | None = None
    cancellation_requested: bool = False
    completed_at: datetime | None = None
    error: str | None = None
    request: _ManagedBatchRequest | None = None
    batch: SimulationBatch | None = None
    thread: Thread | None = None
    lock: Lock = field(default_factory=Lock)


_BATCH_ID_PATTERN = r"batch-[0-9a-f]{12}"
_BATCH_REGISTRY_DIRNAME = "_batches"


def _validate_batch_id(batch_id: str) -> str:
    normalized = batch_id.strip()
    if fullmatch(_BATCH_ID_PATTERN, normalized) is None:
        raise ValidationError("batch_id must match the generated batch identifier format.")
    return normalized


def _batch_registry_root(*, workspace_root: Path) -> Path:
    return (workspace_root / "artifacts" / "sweeps" / _BATCH_REGISTRY_DIRNAME).resolve(strict=False)


def _batch_registry_path(batch_id: str, *, workspace_root: Path) -> Path:
    validated_id = _validate_batch_id(batch_id)
    return (_batch_registry_root(workspace_root=workspace_root) / f"{validated_id}.json").resolve(
        strict=False
    )


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    return datetime.fromisoformat(value)


def _serialize_job(job: _ManagedBatch) -> dict[str, object]:
    return stamp_schema_version(
        {
            "batch_id": job.batch_id,
            "batch_kind": job.batch_kind,
            "source_path": str(job.source_path),
            "output_root": str(job.output_root),
            "manifest_path": str(job.manifest_path),
            "submitted_at": job.submitted_at.isoformat(),
            "status": job.status,
            "run_count": job.run_count,
            "completed_run_count": job.completed_run_count,
            "cancellation_requested": job.cancellation_requested,
            "completed_at": None if job.completed_at is None else job.completed_at.isoformat(),
            "error": job.error,
            "request": None if job.request is None else _serialize_request(job.request),
        }
    )


def _serialize_request(request: _ManagedBatchRequest) -> dict[str, object]:
    return {
        "reference": request.reference,
        "values": request.values,
        "parameters": request.parameters,
        "models": request.models,
        "parallelism": request.parallelism,
        "dry_run": request.dry_run,
        "timeout_s": request.timeout_s,
        "ascii_raw": request.ascii_raw,
        "extra_switches": list(request.extra_switches),
        "resume": request.resume,
        "retained_artifact_policy": request.retained_artifact_policy,
    }


def _deserialize_request(payload: object) -> _ManagedBatchRequest | None:
    if not isinstance(payload, dict):
        return None
    values = payload.get("values")
    parameters = payload.get("parameters")
    models = payload.get("models")
    return _ManagedBatchRequest(
        reference=None if payload.get("reference") is None else str(payload["reference"]),
        values=(
            None
            if values is None
            else [cast("str | int | float", entry) for entry in cast("list[object]", values)]
        ),
        parameters=(
            None
            if parameters is None
            else {
                str(name): [cast("str | int | float | bool", entry) for entry in entries]
                for name, entries in cast("dict[object, list[object]]", parameters).items()
            }
        ),
        models=(None if models is None else [str(item) for item in models]),
        parallelism=int(payload.get("parallelism", 1)),
        dry_run=bool(payload.get("dry_run", False)),
        timeout_s=(None if payload.get("timeout_s") is None else float(payload["timeout_s"])),
        ascii_raw=bool(payload.get("ascii_raw", False)),
        extra_switches=tuple(str(item) for item in payload.get("extra_switches", ())),
        resume=bool(payload.get("resume", False)),
        retained_artifact_policy=cast(
            "RetainedArtifactPolicy",
            str(payload.get("retained_artifact_policy", "cleanup")),
        ),
    )


def _find_persisted_manifest_for_batch_id(
    batch_id: str,
    *,
    workspace_root: Path,
) -> Path | None:
    if not workspace_root.is_dir():
        return None

    logger = get_logger(component="services.batch_manager")
    for manifest_path in workspace_root.rglob("batch.json"):
        try:
            batch = load_batch_manifest(manifest_path, workspace_root=workspace_root)
        except Exception as exc:
            logger.debug(
                "batch_manifest_scan_skipped",
                manifest_path=str(manifest_path),
                error=str(exc),
            )
            continue
        if batch.batch_id == batch_id:
            return manifest_path.resolve(strict=False)
    return None


def _build_restored_job(
    *,
    batch_id: str,
    batch_kind: SweepKind,
    source_path: Path,
    output_root: Path,
    manifest_path: Path,
    submitted_at: datetime,
    status: BatchState,
    run_count: int | None,
    completed_run_count: int,
    cancellation_requested: bool,
    completed_at: datetime | None,
    error: str | None,
    request: _ManagedBatchRequest | None,
    batch: SimulationBatch | None,
) -> _ManagedBatch:
    return _ManagedBatch(
        batch_id=batch_id,
        batch_kind=batch_kind,
        source_path=source_path,
        output_root=output_root,
        manifest_path=manifest_path,
        submitted_at=submitted_at,
        status=status,
        run_count=run_count,
        completed_run_count=completed_run_count,
        cancellation_requested=cancellation_requested,
        completed_at=completed_at,
        error=error,
        request=request,
        batch=batch,
    )


def _restore_job_from_manifest(
    batch: SimulationBatch,
    *,
    request: _ManagedBatchRequest | None = None,
) -> _ManagedBatch:
    completed_run_count = batch.completed_run_count or len(batch.runs)
    error = batch.error
    if (
        batch.status in {"queued", "running", "cancel_requested"}
        and error is None
        and request is None
    ):
        error = (
            "Restored a persisted non-terminal batch snapshot without a live "
            "background manager thread."
        )
    return _build_restored_job(
        batch_id=cast("str", batch.batch_id),
        batch_kind=batch.sweep_kind,
        source_path=batch.source_path,
        output_root=batch.output_root,
        manifest_path=cast("Path", batch.manifest_path),
        submitted_at=batch.submitted_at or datetime.now().astimezone(),
        status=batch.status,
        run_count=batch.run_count,
        completed_run_count=completed_run_count,
        cancellation_requested=batch.status == "cancel_requested",
        completed_at=batch.completed_at,
        error=error,
        request=request,
        batch=batch,
    )


def _require_value_sweep_request(
    reference: str | None,
    values: list[str | int | float] | None,
) -> tuple[str, list[str | int | float]]:
    if reference is None or values is None:
        raise ValueError("Value sweeps require both reference and values.")
    return reference, values


def _require_parameter_sweep_request(
    parameters: dict[str, list[str | int | float | bool]] | None,
) -> dict[str, list[str | int | float | bool]]:
    if parameters is None:
        raise ValueError("Parameter sweeps require a parameters mapping.")
    return parameters


def _require_model_sweep_request(
    reference: str | None,
    models: list[str] | None,
) -> tuple[str, list[str]]:
    if reference is None or models is None:
        raise ValueError("Model sweeps require both reference and models.")
    return reference, models


class SimulationBatchManager:
    """Manage background sweep execution for one MCP server instance."""

    def __init__(self, settings: QSpiceSettings) -> None:
        self.settings = settings.normalized()
        self._jobs: dict[str, _ManagedBatch] = {}

    def _start_job_thread(self, job: _ManagedBatch, *, force_resume: bool | None = None) -> None:
        request = job.request
        if request is None:
            raise ValueError("Cannot start a batch worker without a persisted request.")
        captured_context = copy_context()

        def run_job() -> None:
            captured_context.run(
                self._run_batch,
                job=job,
                reference=request.reference,
                values=request.values,
                parameters=request.parameters,
                models=request.models,
                parallelism=request.parallelism,
                dry_run=request.dry_run,
                timeout_s=request.timeout_s,
                ascii_raw=request.ascii_raw,
                extra_switches=request.extra_switches,
                resume=request.resume if force_resume is None else force_resume,
                retained_artifact_policy=request.retained_artifact_policy,
            )

        thread = Thread(
            target=run_job,
            name=job.batch_id,
            daemon=True,
        )
        job.thread = thread
        thread.start()

    def _maybe_take_over_job(self, job: _ManagedBatch) -> None:
        if job.thread is not None or job.status not in {"queued", "running", "cancel_requested"}:
            return
        if job.request is None:
            if job.error is None:
                job.error = (
                    "Persisted non-terminal batch snapshot could not be resumed because the "
                    "original request details were unavailable."
                )
                self._persist_job(job)
            return
        job.error = None
        self._persist_job(job)
        self._start_job_thread(job, force_resume=True)

    def _persist_job(self, job: _ManagedBatch) -> None:
        payload = _serialize_job(job)
        registry_path = _batch_registry_path(
            job.batch_id,
            workspace_root=self.settings.workspace_root,
        )
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_persisted_job(self, batch_id: str) -> _ManagedBatch:
        validated_id = _validate_batch_id(batch_id)
        registry_path = _batch_registry_path(
            validated_id,
            workspace_root=self.settings.workspace_root,
        )

        if registry_path.is_file():
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            validate_schema_version(
                payload,
                artifact_name="Batch registry entry",
                allow_legacy_unversioned=False,
            )
            job = _build_restored_job(
                batch_id=str(payload["batch_id"]),
                batch_kind=cast("SweepKind", str(payload["batch_kind"])),
                source_path=resolve_workspace_path(
                    str(payload["source_path"]),
                    workspace_root=self.settings.workspace_root,
                ),
                output_root=resolve_workspace_path(
                    str(payload["output_root"]),
                    workspace_root=self.settings.workspace_root,
                ),
                manifest_path=resolve_workspace_path(
                    str(payload["manifest_path"]),
                    workspace_root=self.settings.workspace_root,
                ),
                submitted_at=_parse_datetime(payload.get("submitted_at"))
                or datetime.now().astimezone(),
                status=cast("BatchState", str(payload.get("status", "failed"))),
                run_count=(None if payload.get("run_count") is None else int(payload["run_count"])),
                completed_run_count=int(payload.get("completed_run_count", 0)),
                cancellation_requested=bool(payload.get("cancellation_requested", False)),
                completed_at=_parse_datetime(payload.get("completed_at")),
                error=None if payload.get("error") is None else str(payload["error"]),
                request=_deserialize_request(payload.get("request")),
                batch=None,
            )
        else:
            manifest_path = _find_persisted_manifest_for_batch_id(
                validated_id,
                workspace_root=self.settings.workspace_root,
            )
            if manifest_path is None:
                raise KeyError(validated_id)
            batch = load_batch_manifest(
                manifest_path,
                workspace_root=self.settings.workspace_root,
            )
            if batch.batch_id != validated_id:
                raise KeyError(validated_id)
            job = _restore_job_from_manifest(batch)

        if job.batch_id != validated_id:
            raise KeyError(validated_id)

        if job.manifest_path.is_file():
            batch = load_batch_manifest(
                job.manifest_path,
                workspace_root=self.settings.workspace_root,
            )
            if batch.batch_id != validated_id:
                raise KeyError(validated_id)
            job = _restore_job_from_manifest(batch, request=job.request)

        self._persist_job(job)
        return job

    def _require_job(self, batch_id: str) -> _ManagedBatch:
        validated_id = _validate_batch_id(batch_id)
        job = self._jobs.get(validated_id)
        if job is not None:
            return job
        restored = self._load_persisted_job(validated_id)
        self._jobs[validated_id] = restored
        self._maybe_take_over_job(restored)
        return restored

    def submit_batch(
        self,
        *,
        batch_kind: SweepKind,
        source_path: str,
        reference: str | None = None,
        values: list[str | int | float] | None = None,
        parameters: dict[str, list[str | int | float | bool]] | None = None,
        models: list[str] | None = None,
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: RetainedArtifactPolicy = "cleanup",
    ) -> BatchSubmission:
        """Submit one batch request and return its identifier."""

        resolved_source = resolve_workspace_path(
            source_path, workspace_root=self.settings.workspace_root
        )
        batch_id = f"batch-{uuid4().hex[:12]}"
        output_root = resolve_sweep_output_root(
            output_dir,
            workspace_root=self.settings.workspace_root,
            source_path=resolved_source,
            sweep_kind=batch_kind,
        )
        manifest_path = batch_manifest_path(output_root)
        submitted_at = datetime.now().astimezone()
        request = _ManagedBatchRequest(
            reference=reference,
            values=values,
            parameters=parameters,
            models=models,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        job = _ManagedBatch(
            batch_id=batch_id,
            batch_kind=batch_kind,
            source_path=resolved_source,
            output_root=output_root,
            manifest_path=manifest_path,
            submitted_at=submitted_at,
            request=request,
        )
        self._jobs[batch_id] = job
        self._persist_job(job)
        logger = get_logger(component="services.batch_manager", batch_id=batch_id)
        logger.info(
            "batch_submission_accepted",
            batch_kind=batch_kind,
            dry_run=dry_run,
            parallelism=parallelism,
            resume=resume,
        )
        self._start_job_thread(job)

        return BatchSubmission(
            batch_id=batch_id,
            batch_kind=batch_kind,
            status="queued",
            source_path=resolved_source,
            output_root=output_root,
            manifest_path=manifest_path,
            submitted_at=submitted_at,
        )

    def get_batch_status(self, batch_id: str) -> BatchStatus:
        """Return the live or final status for one batch."""

        job = self._require_job(batch_id)
        with job.lock:
            return BatchStatus(
                batch_id=job.batch_id,
                batch_kind=job.batch_kind,
                status=job.status,
                source_path=job.source_path,
                output_root=job.output_root,
                manifest_path=job.manifest_path,
                run_count=job.run_count,
                completed_run_count=job.completed_run_count,
                cancellation_requested=job.cancellation_requested,
                submitted_at=job.submitted_at,
                completed_at=job.completed_at,
                error=job.error,
            )

    def cancel_batch(self, batch_id: str) -> BatchCancellation:
        """Request cancellation for one running or queued batch."""

        job = self._require_job(batch_id)
        with job.lock:
            if job.status in {"completed", "failed", "canceled"}:
                note = "Batch is already in a terminal state."
            elif job.thread is None:
                note = (
                    "Batch was restored from persisted state without a live manager "
                    "thread. Cancellation is unavailable after restart."
                )
            else:
                job.cancellation_requested = True
                if job.status == "queued":
                    job.status = "cancel_requested"
                note = (
                    "Cancellation requested. The current implementation stops "
                    "between runs, not mid-simulation."
                )
            self._persist_job(job)
            return BatchCancellation(
                batch_id=job.batch_id,
                batch_kind=job.batch_kind,
                status=job.status,
                output_root=job.output_root,
                cancellation_requested=job.cancellation_requested,
                note=note,
            )

    def collect_batch_results(self, batch_id: str) -> BatchCollection:
        """Return completed batch results when they are available."""

        job = self._require_job(batch_id)
        with job.lock:
            if job.status in {"queued", "running", "cancel_requested"}:
                return BatchCollection(
                    batch_id=job.batch_id,
                    status=job.status,
                    batch=None,
                    error="Batch is not complete yet.",
                )
            if job.status == "failed":
                return BatchCollection(
                    batch_id=job.batch_id, status=job.status, batch=None, error=job.error
                )
            if job.batch is not None:
                return BatchCollection(batch_id=job.batch_id, status=job.status, batch=job.batch)

        try:
            loaded = load_batch_manifest(
                job.manifest_path,
                workspace_root=self.settings.workspace_root,
            )
        except Exception as exc:
            return BatchCollection(
                batch_id=batch_id,
                status=job.status,
                batch=None,
                error=job.error or f"Persisted batch manifest could not be loaded: {exc}",
            )
        with job.lock:
            job.batch = loaded
            job.status = loaded.status
            job.run_count = loaded.run_count
            job.completed_run_count = loaded.completed_run_count or len(loaded.runs)
            job.completed_at = loaded.completed_at
            job.error = loaded.error
            self._persist_job(job)
        return BatchCollection(batch_id=batch_id, status=loaded.status, batch=loaded)

    def _run_batch(
        self,
        *,
        job: _ManagedBatch,
        reference: str | None,
        values: list[str | int | float] | None,
        parameters: dict[str, list[str | int | float | bool]] | None,
        models: list[str] | None,
        parallelism: int,
        dry_run: bool,
        timeout_s: float | None,
        ascii_raw: bool,
        extra_switches: tuple[str, ...],
        resume: bool,
        retained_artifact_policy: RetainedArtifactPolicy,
    ) -> None:
        """Execute one queued batch in a background thread."""

        logger = get_logger(
            component="services.batch_manager",
            batch_id=job.batch_id,
            batch_kind=job.batch_kind,
        )

        with job.lock:
            if job.cancellation_requested:
                job.status = "canceled"
                job.completed_at = datetime.now().astimezone()
                self._persist_job(job)
                return
            job.status = "running"
            self._persist_job(job)

        def should_cancel() -> bool:
            return job.cancellation_requested

        def on_run_complete(_: object) -> None:
            with job.lock:
                job.completed_run_count += 1

        logger.info("batch_execution_started", dry_run=dry_run, resume=resume)
        try:
            with operation_span(
                "batch.execute",
                enabled=self.settings.telemetry_enabled,
                attributes={
                    "qspice.batch_id": job.batch_id,
                    "qspice.batch_kind": job.batch_kind,
                    "qspice.parallelism": parallelism,
                },
            ):
                if job.batch_kind == "component_value":
                    reference, values = _require_value_sweep_request(reference, values)
                    batch = run_value_sweep(
                        job.source_path,
                        workspace_root=self.settings.workspace_root,
                        reference=reference,
                        values=values,
                        settings=self.settings,
                        output_dir=job.output_root,
                        parallelism=parallelism,
                        dry_run=dry_run,
                        timeout_s=timeout_s,
                        ascii_raw=ascii_raw,
                        extra_switches=extra_switches,
                        resume=resume,
                        retained_artifact_policy=retained_artifact_policy,
                        batch_id=job.batch_id,
                        should_cancel=should_cancel,
                        on_run_complete=on_run_complete,
                    )
                elif job.batch_kind == "parameter":
                    parameters = _require_parameter_sweep_request(parameters)
                    batch = run_param_sweep(
                        job.source_path,
                        workspace_root=self.settings.workspace_root,
                        parameters=parameters,
                        settings=self.settings,
                        output_dir=job.output_root,
                        parallelism=parallelism,
                        dry_run=dry_run,
                        timeout_s=timeout_s,
                        ascii_raw=ascii_raw,
                        extra_switches=extra_switches,
                        resume=resume,
                        retained_artifact_policy=retained_artifact_policy,
                        batch_id=job.batch_id,
                        should_cancel=should_cancel,
                        on_run_complete=on_run_complete,
                    )
                else:
                    reference, models = _require_model_sweep_request(reference, models)
                    batch = run_model_sweep(
                        job.source_path,
                        workspace_root=self.settings.workspace_root,
                        reference=reference,
                        models=models,
                        settings=self.settings,
                        output_dir=job.output_root,
                        parallelism=parallelism,
                        dry_run=dry_run,
                        timeout_s=timeout_s,
                        ascii_raw=ascii_raw,
                        extra_switches=extra_switches,
                        resume=resume,
                        retained_artifact_policy=retained_artifact_policy,
                        batch_id=job.batch_id,
                        should_cancel=should_cancel,
                        on_run_complete=on_run_complete,
                    )
        except Exception as exc:
            logger.exception("batch_execution_failed")
            with job.lock:
                job.status = "failed"
                job.error = str(exc)
                job.completed_at = datetime.now().astimezone()
                self._persist_job(job)
            return

        with job.lock:
            job.batch = batch
            job.status = batch.status
            job.run_count = batch.run_count
            job.completed_run_count = batch.completed_run_count or len(batch.runs)
            job.completed_at = batch.completed_at
            job.manifest_path = batch.manifest_path or job.manifest_path
            job.error = batch.error
            self._persist_job(job)
        logger.info(
            "batch_execution_completed",
            status=batch.status,
            run_count=batch.run_count,
            completed_run_count=batch.completed_run_count or len(batch.runs),
        )


__all__ = ["SimulationBatchManager"]
