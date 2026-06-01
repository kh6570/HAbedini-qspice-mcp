"""Service metadata for downloading remote-style simulation artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

RemoteSessionState = Literal["queued", "running", "completed", "failed", "closed"]


@dataclass(frozen=True, slots=True)
class RemoteArtifactDownload:
    """Metadata for one packaged remote-style artifact bundle."""

    session_id: str
    status: RemoteSessionState
    output_path: Path
    artifact_kinds: tuple[str, ...]
    entry_names: tuple[str, ...]
    artifact_count: int
    bundle_size_bytes: int


SERVICE_SPEC = ServiceSpec(
    name="download_remote_artifacts",
    title="Download Remote Artifacts",
    summary="Package selected remote-style simulation artifacts into one zip bundle.",
    phase="implemented",
    read_only=False,
)


__all__ = ["SERVICE_SPEC", "RemoteArtifactDownload"]
