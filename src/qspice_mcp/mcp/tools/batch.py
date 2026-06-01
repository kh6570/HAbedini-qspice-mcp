"""Background batch tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .shared import to_json_object

BatchKind = Literal["component_value", "parameter", "model"]

if TYPE_CHECKING:
    from ._protocols import SupportsBatchRuntime as _RuntimeWithBatch
else:
    _RuntimeWithBatch = object

BATCH_HANDLER_NAMES = (
    "submit_batch",
    "get_batch_status",
    "collect_batch_results",
    "cancel_batch",
)


class BatchToolMixin:
    """Handlers for background batch lifecycle tools."""

    def submit_batch(
        self: _RuntimeWithBatch,
        batch_kind: BatchKind,
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
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        submission = self._batch_manager.submit_batch(
            batch_kind=batch_kind,
            source_path=source_path,
            reference=reference,
            values=values,
            parameters=parameters,
            models=models,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=extra_switches,
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(submission)

    def get_batch_status(self: _RuntimeWithBatch, batch_id: str) -> dict[str, object]:
        return to_json_object(self._batch_manager.get_batch_status(batch_id))

    def collect_batch_results(self: _RuntimeWithBatch, batch_id: str) -> dict[str, object]:
        return to_json_object(self._batch_manager.collect_batch_results(batch_id))

    def cancel_batch(self: _RuntimeWithBatch, batch_id: str) -> dict[str, object]:
        return to_json_object(self._batch_manager.cancel_batch(batch_id))


__all__ = ["BATCH_HANDLER_NAMES", "BatchToolMixin"]
