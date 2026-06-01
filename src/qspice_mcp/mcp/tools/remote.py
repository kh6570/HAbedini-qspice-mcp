"""Remote-style simulation lifecycle tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsRemoteRuntime as _RuntimeWithRemote
else:
    _RuntimeWithRemote = object

REMOTE_HANDLER_NAMES = (
    "submit_remote_simulation",
    "poll_remote_run",
    "download_remote_artifacts",
    "close_remote_session",
)


class RemoteToolMixin:
    """Handlers for remote-style lifecycle and artifact transport tools."""

    def submit_remote_simulation(
        self: _RuntimeWithRemote,
        source_path: str,
        output_dir: str | None = None,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
    ) -> dict[str, object]:
        submission = self._remote_manager.submit_remote_simulation(
            source_path=source_path,
            output_dir=output_dir,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=extra_switches,
        )
        return to_json_object(submission)

    def poll_remote_run(self: _RuntimeWithRemote, session_id: str) -> dict[str, object]:
        return to_json_object(self._remote_manager.poll_remote_run(session_id))

    def download_remote_artifacts(
        self: _RuntimeWithRemote,
        session_id: str,
        output_path: str | None = None,
        artifact_kinds: list[str] | None = None,
    ) -> dict[str, object]:
        return to_json_object(
            self._remote_manager.download_remote_artifacts(
                session_id,
                output_path=output_path,
                artifact_kinds=artifact_kinds,
            )
        )

    def close_remote_session(
        self: _RuntimeWithRemote,
        session_id: str,
        delete_bundle: bool = False,
    ) -> dict[str, object]:
        return to_json_object(
            self._remote_manager.close_remote_session(
                session_id,
                delete_bundle=delete_bundle,
            )
        )


__all__ = ["REMOTE_HANDLER_NAMES", "RemoteToolMixin"]
