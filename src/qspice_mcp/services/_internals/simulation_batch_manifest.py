"""Persisted manifest and run-record helpers for simulation batches."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from re import sub
from typing import Any

from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file

from .simulation_batch_models import BatchState, SimulationBatch, SimulationBatchRun, SweepKind

_BATCH_RUN_RECORD_NAME = "run.json"


def slugify(value: str) -> str:
    """Return a filesystem-friendly slug for one label."""

    collapsed = sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return collapsed.lower() or "run"


def batch_manifest_path(output_root: Path) -> Path:
    """Return the default manifest path for one batch output root."""

    return (output_root / "batch.json").resolve(strict=False)


def build_run_paths(
    source_path: Path,
    *,
    output_root: Path,
    index: int,
    label: str,
) -> tuple[Path, Path, Path, Path]:
    """Return per-run schematic, netlist, log, and raw paths."""

    run_dir = (output_root / f"run-{index:03d}-{slugify(label)}").resolve(strict=False)
    return (
        run_dir / source_path.name,
        run_dir / source_path.with_suffix(".net").name,
        run_dir / source_path.with_suffix(".log").name,
        run_dir / source_path.with_suffix(".qraw").name,
    )


def batch_run_record_path(
    source_path: Path,
    *,
    output_root: Path,
    index: int,
    label: str,
) -> Path:
    """Return the persisted sidecar path for one realized batch run."""

    return (
        build_run_paths(source_path, output_root=output_root, index=index, label=label)[0].parent
        / _BATCH_RUN_RECORD_NAME
    ).resolve(strict=False)


def _jsonify(value: Any) -> Any:
    """Convert batch dataclasses into JSON-friendly data."""

    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _jsonify(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {name: _jsonify(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


def save_batch_manifest(batch: SimulationBatch) -> SimulationBatch:
    """Persist one batch manifest below its output root."""

    manifest = batch_manifest_path(batch.output_root)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    persisted = SimulationBatch(
        source_path=batch.source_path,
        output_root=batch.output_root,
        sweep_kind=batch.sweep_kind,
        run_count=batch.run_count,
        parallelism=batch.parallelism,
        sequential=batch.sequential,
        runs=batch.runs,
        reference=batch.reference,
        parameter_names=batch.parameter_names,
        warnings=batch.warnings,
        batch_id=batch.batch_id,
        status=batch.status,
        completed_run_count=batch.completed_run_count,
        manifest_path=manifest,
        submitted_at=batch.submitted_at,
        completed_at=batch.completed_at,
        error=batch.error,
        plan_path=batch.plan_path,
        seed=batch.seed,
    )
    manifest.write_text(
        json.dumps(stamp_schema_version(_jsonify(persisted)), indent=2),
        encoding="utf-8",
    )
    return persisted


def save_batch_run_record(run: SimulationBatchRun) -> Path:
    """Persist one per-run sidecar record for resumable recovery."""

    record_path = (run.schematic_path.parent / _BATCH_RUN_RECORD_NAME).resolve(strict=False)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(stamp_schema_version(_jsonify(run)), indent=2),
        encoding="utf-8",
    )
    return record_path


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse one ISO timestamp when present."""

    if not value:
        return None
    return datetime.fromisoformat(value)


def load_batch_manifest(
    raw_path: str | Path,
    *,
    workspace_root: Path,
) -> SimulationBatch:
    """Load a batch manifest from a batch root or explicit json path."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved = resolve_workspace_path(raw_path, workspace_root=normalized_workspace)
    manifest = resolved if resolved.suffix.lower() == ".json" else batch_manifest_path(resolved)
    validated = validate_existing_file(
        manifest,
        workspace_root=normalized_workspace,
        suffixes=(".json",),
    )
    payload = json.loads(validated.read_text(encoding="utf-8"))
    validate_schema_version(
        payload,
        artifact_name="Batch manifest",
        allow_legacy_unversioned=True,
    )

    def resolve_persisted_path(value: object) -> Path:
        return resolve_workspace_path(str(value), workspace_root=normalized_workspace)

    runs = tuple(
        SimulationBatchRun(
            index=int(item["index"]),
            label=str(item["label"]),
            assignment=dict(item.get("assignment", {})),
            schematic_path=resolve_persisted_path(item["schematic_path"]),
            netlist_path=resolve_persisted_path(item["netlist_path"]),
            log_path=resolve_persisted_path(item["log_path"]),
            raw_path=resolve_persisted_path(item["raw_path"]),
            command=tuple(str(value) for value in item.get("command", ())),
            dry_run=bool(item.get("dry_run", False)),
            exit_code=None if item.get("exit_code") is None else int(item["exit_code"]),
            duration_s=None if item.get("duration_s") is None else float(item["duration_s"]),
            warnings=tuple(str(value) for value in item.get("warnings", ())),
        )
        for item in payload.get("runs", [])
    )
    return SimulationBatch(
        source_path=resolve_persisted_path(payload["source_path"]),
        output_root=resolve_persisted_path(payload["output_root"]),
        sweep_kind=payload["sweep_kind"],
        run_count=int(payload["run_count"]),
        parallelism=int(payload["parallelism"]),
        sequential=bool(payload["sequential"]),
        runs=runs,
        reference=payload.get("reference"),
        parameter_names=tuple(str(value) for value in payload.get("parameter_names", ())),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
        batch_id=payload.get("batch_id"),
        status=payload.get("status", "completed"),
        completed_run_count=(
            None
            if payload.get("completed_run_count") is None
            else int(payload["completed_run_count"])
        ),
        manifest_path=validated,
        submitted_at=_parse_datetime(payload.get("submitted_at")),
        completed_at=_parse_datetime(payload.get("completed_at")),
        error=payload.get("error"),
        plan_path=(
            None
            if payload.get("plan_path") is None
            else resolve_persisted_path(payload["plan_path"])
        ),
        seed=None if payload.get("seed") is None else int(payload["seed"]),
    )


def load_batch_run_record(
    raw_path: str | Path,
    *,
    workspace_root: Path,
) -> SimulationBatchRun:
    """Load one persisted per-run sidecar record."""

    validated = validate_existing_file(raw_path, workspace_root=workspace_root, suffixes=(".json",))
    payload = json.loads(validated.read_text(encoding="utf-8"))
    validate_schema_version(
        payload,
        artifact_name="Batch run record",
        allow_legacy_unversioned=False,
    )

    def resolve_persisted_path(value: object) -> Path:
        return resolve_workspace_path(str(value), workspace_root=workspace_root)

    return SimulationBatchRun(
        index=int(payload["index"]),
        label=str(payload["label"]),
        assignment=dict(payload.get("assignment", {})),
        schematic_path=resolve_persisted_path(payload["schematic_path"]),
        netlist_path=resolve_persisted_path(payload["netlist_path"]),
        log_path=resolve_persisted_path(payload["log_path"]),
        raw_path=resolve_persisted_path(payload["raw_path"]),
        command=tuple(str(value) for value in payload.get("command", ())),
        dry_run=bool(payload.get("dry_run", False)),
        exit_code=None if payload.get("exit_code") is None else int(payload["exit_code"]),
        duration_s=None if payload.get("duration_s") is None else float(payload["duration_s"]),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
    )


def _build_batch_snapshot(
    *,
    source_path: Path,
    output_root: Path,
    sweep_kind: SweepKind,
    run_count: int,
    parallelism: int,
    sequential: bool,
    runs: tuple[SimulationBatchRun, ...],
    warnings: tuple[str, ...],
    batch_id: str | None,
    status: BatchState,
    submitted_at: datetime,
    completed_at: datetime | None = None,
    reference: str | None = None,
    parameter_names: tuple[str, ...] = (),
    plan_path: Path | None = None,
    seed: int | None = None,
) -> SimulationBatch:
    return SimulationBatch(
        source_path=source_path,
        output_root=output_root,
        sweep_kind=sweep_kind,
        run_count=run_count,
        parallelism=parallelism,
        sequential=sequential,
        runs=tuple(sorted(runs, key=lambda run: run.index)),
        reference=reference,
        parameter_names=parameter_names,
        warnings=tuple(dict.fromkeys(warnings)),
        batch_id=batch_id,
        status=status,
        completed_run_count=len(runs),
        submitted_at=submitted_at,
        completed_at=completed_at,
        plan_path=plan_path,
        seed=seed,
    )


__all__ = [
    "batch_manifest_path",
    "batch_run_record_path",
    "build_run_paths",
    "load_batch_manifest",
    "load_batch_run_record",
    "save_batch_manifest",
    "save_batch_run_record",
    "slugify",
]
