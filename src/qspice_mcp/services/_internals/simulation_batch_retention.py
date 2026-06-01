"""Retained-run reuse and artifact cleanup helpers for simulation batches."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING, cast

from .simulation_batch_manifest import (
    batch_manifest_path,
    batch_run_record_path,
    build_run_paths,
    load_batch_manifest,
    load_batch_run_record,
)
from .simulation_batch_models import (
    _RETAINED_ARTIFACT_POLICIES,
    ResumableBatchState,
    RetainedArtifactPolicy,
    SimulationBatch,
    SimulationBatchRun,
    SweepKind,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


def load_resumable_batch_state(
    *,
    output_root: Path,
    workspace_root: Path,
    source_path: Path,
    sweep_kind: SweepKind,
    expected_runs: Sequence[tuple[int, str, Mapping[str, object]]],
    reference: str | None = None,
    parameter_names: Sequence[str] = (),
    plan_path: Path | None = None,
    seed: int | None = None,
) -> ResumableBatchState:
    """Load successful runs from an existing manifest when it matches the request."""

    manifest = batch_manifest_path(output_root)
    if not manifest.is_file():
        return ResumableBatchState()

    existing = load_batch_manifest(manifest, workspace_root=workspace_root)
    _validate_resumable_batch_metadata(
        existing=existing,
        source_path=source_path,
        sweep_kind=sweep_kind,
        expected_run_count=len(expected_runs),
        reference=reference,
        parameter_names=parameter_names,
        plan_path=plan_path,
        seed=seed,
    )
    successful_runs = _collect_resumed_runs(existing=existing, expected_runs=expected_runs)
    recovered_runs, recovery_warnings = _recover_runs_from_sidecars(
        source_path=source_path,
        output_root=output_root,
        workspace_root=workspace_root,
        expected_runs=expected_runs,
        existing_runs=existing.runs,
    )
    if recovered_runs:
        successful_runs.extend(recovered_runs)
    resumed_runs, retry_indexes = _partition_reusable_runs(successful_runs)
    warnings: list[str] = list(recovery_warnings)
    if retry_indexes:
        warnings.append(
            f"Retrying {len(retry_indexes)} run(s) because retained artifacts were missing."
        )

    if not resumed_runs:
        return ResumableBatchState(
            warnings=tuple(warnings),
            submitted_at=existing.submitted_at,
            batch_id=existing.batch_id,
            had_manifest=True,
        )

    reused_indexes = frozenset(run.index for run in resumed_runs)
    warnings.append(
        f"Reused {len(reused_indexes)} previously successful run(s) from the existing "
        "batch manifest."
    )
    return ResumableBatchState(
        resumed_runs=tuple(sorted(resumed_runs, key=lambda run: run.index)),
        completed_indexes=reused_indexes,
        warnings=tuple(warnings),
        submitted_at=existing.submitted_at,
        batch_id=existing.batch_id,
        had_manifest=True,
    )


def _validate_resumable_batch_metadata(
    *,
    existing: SimulationBatch,
    source_path: Path,
    sweep_kind: SweepKind,
    expected_run_count: int,
    reference: str | None,
    parameter_names: Sequence[str],
    plan_path: Path | None,
    seed: int | None,
) -> None:
    checks = (
        (
            existing.source_path != source_path.resolve(strict=False),
            "output_dir already contains a batch for a different source path.",
        ),
        (
            existing.sweep_kind != sweep_kind,
            "output_dir already contains a batch for a different sweep kind.",
        ),
        (
            existing.reference != reference,
            "output_dir already contains a batch for a different reference.",
        ),
        (
            tuple(existing.parameter_names) != tuple(parameter_names),
            "output_dir already contains a batch for different parameters.",
        ),
        (
            existing.plan_path != plan_path,
            "output_dir already contains a batch for a different prepared plan.",
        ),
        (
            existing.seed != seed,
            "output_dir already contains a batch for a different random seed.",
        ),
        (
            existing.run_count != expected_run_count,
            "output_dir already contains a batch with a different run count.",
        ),
    )
    for mismatched, message in checks:
        if mismatched:
            raise ValueError(message)


def _collect_resumed_runs(
    *,
    existing: SimulationBatch,
    expected_runs: Sequence[tuple[int, str, Mapping[str, object]]],
) -> list[SimulationBatchRun]:
    expected_by_index = {
        index: (label, dict(assignment)) for index, label, assignment in expected_runs
    }
    resumed_runs: list[SimulationBatchRun] = []
    for run in existing.runs:
        expected = expected_by_index.get(run.index)
        if expected is None:
            raise ValueError("output_dir already contains a batch with unexpected run indexes.")
        expected_label, expected_assignment = expected
        if run.label != expected_label or run.assignment != expected_assignment:
            raise ValueError(
                "output_dir already contains a batch whose run labels or assignments do not "
                "match the requested workload."
            )
        if run.exit_code == 0:
            resumed_runs.append(run)
    return resumed_runs


def _partition_reusable_runs(
    successful_runs: Sequence[SimulationBatchRun],
) -> tuple[list[SimulationBatchRun], tuple[int, ...]]:
    reusable_runs: list[SimulationBatchRun] = []
    retry_indexes: list[int] = []
    for run in successful_runs:
        if _retained_run_artifacts_exist(run):
            reusable_runs.append(run)
            continue
        retry_indexes.append(run.index)
    return reusable_runs, tuple(retry_indexes)


def _recover_runs_from_sidecars(
    *,
    source_path: Path,
    output_root: Path,
    workspace_root: Path,
    expected_runs: Sequence[tuple[int, str, Mapping[str, object]]],
    existing_runs: Sequence[SimulationBatchRun],
) -> tuple[list[SimulationBatchRun], tuple[str, ...]]:
    existing_by_index = {run.index: run for run in existing_runs}
    recovered_runs: list[SimulationBatchRun] = []

    for index, label, assignment in expected_runs:
        if index in existing_by_index:
            continue
        record_path = batch_run_record_path(
            source_path,
            output_root=output_root,
            index=index,
            label=label,
        )
        if not record_path.is_file():
            continue
        recovered = load_batch_run_record(record_path, workspace_root=workspace_root)
        if recovered.label != label or recovered.assignment != dict(assignment):
            raise ValueError(
                "output_dir already contains persisted run records whose labels or assignments "
                "do not match the requested workload."
            )
        if recovered.exit_code == 0:
            recovered_runs.append(recovered)

    if not recovered_runs:
        return [], ()

    return recovered_runs, (
        f"Recovered {len(recovered_runs)} completed run(s) from per-run sidecars that were newer "
        "than the batch manifest.",
    )


def _retained_run_artifacts_exist(run: SimulationBatchRun) -> bool:
    if run.dry_run:
        return True
    return all(
        path.is_file()
        for path in (run.schematic_path, run.netlist_path, run.log_path, run.raw_path)
    )


def _normalize_retained_artifact_policy(policy: str) -> RetainedArtifactPolicy:
    normalized = policy.strip().lower()
    if normalized not in _RETAINED_ARTIFACT_POLICIES:
        choices = ", ".join(sorted(_RETAINED_ARTIFACT_POLICIES))
        raise ValueError(f"retained_artifact_policy must be one of: {choices}.")
    return cast("RetainedArtifactPolicy", normalized)


def _should_remove_stale_retry_artifacts(policy: RetainedArtifactPolicy) -> bool:
    return policy in {"cleanup", "keep_orphans"}


def _should_remove_orphaned_artifacts(policy: RetainedArtifactPolicy) -> bool:
    return policy in {"cleanup", "keep_stale"}


def _remove_retained_artifact_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _prepare_retained_artifacts(
    *,
    output_root: Path,
    source_path: Path,
    planned_runs: Sequence[
        tuple[int, str, Mapping[str, object], Callable[[_QschEditorProtocol], None]]
    ],
    completed_indexes: frozenset[int],
    resume: bool,
    had_manifest: bool,
    retained_artifact_policy: RetainedArtifactPolicy,
) -> tuple[str, ...]:
    if not output_root.is_dir():
        return ()

    expected_run_dirs = {
        index: build_run_paths(
            source_path,
            output_root=output_root,
            index=index,
            label=label,
        )[0].parent.resolve(strict=False)
        for index, label, _, _ in planned_runs
    }
    stale_retry_paths: list[Path] = []
    retry_indexes = frozenset(
        index for index in expected_run_dirs if index not in completed_indexes
    )
    for index in retry_indexes:
        run_dir = expected_run_dirs[index]
        if not run_dir.exists():
            continue
        stale_retry_paths.append(run_dir)

    if _should_remove_stale_retry_artifacts(retained_artifact_policy):
        for run_dir in stale_retry_paths:
            _remove_retained_artifact_path(run_dir)

    expected_paths = frozenset(expected_run_dirs.values())
    orphaned_paths = [
        entry.resolve(strict=False)
        for entry in output_root.iterdir()
        if entry.name.startswith("run-") and entry.resolve(strict=False) not in expected_paths
    ]
    if _should_remove_orphaned_artifacts(retained_artifact_policy):
        for orphaned_path in orphaned_paths:
            _remove_retained_artifact_path(orphaned_path)

    warnings: list[str] = []
    if resume and had_manifest and retry_indexes:
        warnings.append(
            f"Retrying {len(retry_indexes)} retained run(s) that were not previously reusable."
        )
    stale_retry_count = len(stale_retry_paths)
    if stale_retry_count:
        stale_action = (
            "Removed"
            if _should_remove_stale_retry_artifacts(retained_artifact_policy)
            else "Preserved"
        )
        stale_suffix = (
            "before rerun."
            if stale_action == "Removed"
            else (f"before rerun because retained_artifact_policy={retained_artifact_policy!r}.")
        )
        warnings.append(
            f"{stale_action} {stale_retry_count} stale run artifact director"
            f"{'y' if stale_retry_count == 1 else 'ies'} {stale_suffix}"
        )
    if orphaned_paths:
        orphan_count = len(orphaned_paths)
        orphan_action = (
            "Removed"
            if _should_remove_orphaned_artifacts(retained_artifact_policy)
            else "Preserved"
        )
        orphan_suffix = (
            "outside the requested workload."
            if orphan_action == "Removed"
            else (
                "outside the requested workload because "
                f"retained_artifact_policy={retained_artifact_policy!r}."
            )
        )
        warnings.append(
            f"{orphan_action} {orphan_count} orphaned run artifact director"
            f"{'y' if orphan_count == 1 else 'ies'} {orphan_suffix}"
        )
    return tuple(warnings)


__all__ = ["load_resumable_batch_state"]
