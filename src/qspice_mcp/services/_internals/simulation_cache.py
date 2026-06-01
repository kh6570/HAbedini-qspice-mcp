"""Hash-addressed simulation artifact cache."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class CachedSimulationArtifacts:
    """One cached successful simulation artifact set."""

    key: str
    root: Path
    log_path: Path
    raw_path: Path
    metadata_path: Path
    created_at: datetime
    exit_code: int
    duration_s: float | None
    stdout: str
    stderr: str


class SimulationArtifactCache:
    """Manage cached successful simulation outputs keyed by input content."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=False)

    def _entry_root(self, key: str) -> Path:
        return (self.root / key).resolve(strict=False)

    def _metadata_path(self, key: str) -> Path:
        return (self._entry_root(key) / "metadata.json").resolve(strict=False)

    def build_key(
        self,
        *,
        netlist_path: Path,
        adapter_key: str,
        executable: str,
        extra_switches: Sequence[str],
        ascii_raw: bool,
    ) -> str:
        netlist_hash = hashlib.sha256(netlist_path.read_bytes()).hexdigest()
        payload = json.dumps(
            {
                "adapter_key": adapter_key,
                "ascii_raw": ascii_raw,
                "executable": executable,
                "extra_switches": list(extra_switches),
                "netlist_hash": netlist_hash,
            },
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, key: str) -> CachedSimulationArtifacts | None:
        metadata_path = self._metadata_path(key)
        if not metadata_path.is_file():
            return None
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        validate_schema_version(
            payload,
            artifact_name="Simulation cache metadata",
            allow_legacy_unversioned=False,
        )
        entry_root = self._entry_root(key)
        log_path = (entry_root / "artifacts.log").resolve(strict=False)
        raw_path = (entry_root / "artifacts.qraw").resolve(strict=False)
        if not log_path.is_file() or not raw_path.is_file():
            self.invalidate(key)
            return None
        return CachedSimulationArtifacts(
            key=key,
            root=entry_root,
            log_path=log_path,
            raw_path=raw_path,
            metadata_path=metadata_path,
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            exit_code=int(payload["exit_code"]),
            duration_s=(
                None if payload.get("duration_s") is None else float(payload["duration_s"])
            ),
            stdout=str(payload.get("stdout", "")),
            stderr=str(payload.get("stderr", "")),
        )

    def put(
        self,
        key: str,
        *,
        log_source: Path,
        raw_source: Path,
        exit_code: int,
        duration_s: float | None,
        stdout: str,
        stderr: str,
    ) -> CachedSimulationArtifacts:
        entry_root = self._entry_root(key)
        entry_root.mkdir(parents=True, exist_ok=True)
        cached_log = (entry_root / "artifacts.log").resolve(strict=False)
        cached_raw = (entry_root / "artifacts.qraw").resolve(strict=False)
        shutil.copy2(log_source, cached_log)
        shutil.copy2(raw_source, cached_raw)
        created_at = datetime.now().astimezone()
        payload: dict[str, Any] = stamp_schema_version(
            {
                "created_at": created_at.isoformat(),
                "duration_s": duration_s,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        metadata_path = self._metadata_path(key)
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return CachedSimulationArtifacts(
            key=key,
            root=entry_root,
            log_path=cached_log,
            raw_path=cached_raw,
            metadata_path=metadata_path,
            created_at=created_at,
            exit_code=exit_code,
            duration_s=duration_s,
            stdout=stdout,
            stderr=stderr,
        )

    def materialize(
        self,
        entry: CachedSimulationArtifacts,
        *,
        log_destination: Path,
        raw_destination: Path,
    ) -> None:
        log_destination.parent.mkdir(parents=True, exist_ok=True)
        raw_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(entry.log_path, log_destination)
        shutil.copy2(entry.raw_path, raw_destination)

    def invalidate(self, key: str) -> None:
        entry_root = self._entry_root(key)
        if entry_root.exists():
            shutil.rmtree(entry_root)


__all__ = ["CachedSimulationArtifacts", "SimulationArtifactCache"]
