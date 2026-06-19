"""Hash-addressed simulation artifact cache."""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
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


def _artifact_integrity_hash(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _entry_byte_size(entry_root: Path) -> int:
    total = 0
    for path in entry_root.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    return total


class SimulationArtifactCache:
    """Manage cached successful simulation outputs keyed by input content."""

    def __init__(self, root: Path, *, max_cache_bytes: int | None = None) -> None:
        self.root = root.resolve(strict=False)
        self.max_cache_bytes = max_cache_bytes

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
        executable_version: str | None = None,
        executable_mtime: float | None = None,
        extra_switches: Sequence[str],
        ascii_raw: bool,
    ) -> str:
        netlist_hash = hashlib.sha256(netlist_path.read_bytes()).hexdigest()
        payload = json.dumps(
            {
                "adapter_key": adapter_key,
                "ascii_raw": ascii_raw,
                "executable": executable,
                "executable_mtime": executable_mtime,
                "executable_version": executable_version,
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
        expected_integrity = payload.get("integrity_hash")
        if isinstance(expected_integrity, str):
            actual_integrity = _artifact_integrity_hash(log_path, raw_path)
            if actual_integrity != expected_integrity:
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
        self.root.mkdir(parents=True, exist_ok=True)
        staging_root = (self.root / f".staging-{key[:12]}-{uuid.uuid4().hex}").resolve(strict=False)
        staging_root.mkdir(parents=True, exist_ok=False)
        cached_log = (staging_root / "artifacts.log").resolve(strict=False)
        cached_raw = (staging_root / "artifacts.qraw").resolve(strict=False)
        shutil.copy2(log_source, cached_log)
        shutil.copy2(raw_source, cached_raw)
        integrity_hash = _artifact_integrity_hash(cached_log, cached_raw)
        created_at = datetime.now().astimezone()
        payload: dict[str, Any] = stamp_schema_version(
            {
                "created_at": created_at.isoformat(),
                "duration_s": duration_s,
                "exit_code": exit_code,
                "integrity_hash": integrity_hash,
                "stdout": stdout,
                "stderr": stderr,
            }
        )
        metadata_path = (staging_root / "metadata.json").resolve(strict=False)
        metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        entry_root = self._entry_root(key)
        if entry_root.exists():
            shutil.rmtree(entry_root)
        staging_root.replace(entry_root)
        self._evict_if_needed()

        final_log = (entry_root / "artifacts.log").resolve(strict=False)
        final_raw = (entry_root / "artifacts.qraw").resolve(strict=False)
        final_metadata = self._metadata_path(key)
        return CachedSimulationArtifacts(
            key=key,
            root=entry_root,
            log_path=final_log,
            raw_path=final_raw,
            metadata_path=final_metadata,
            created_at=created_at,
            exit_code=exit_code,
            duration_s=duration_s,
            stdout=stdout,
            stderr=stderr,
        )

    def _evict_if_needed(self) -> None:
        if self.max_cache_bytes is None or self.max_cache_bytes <= 0:
            return
        entries: list[tuple[str, Path, int]] = []
        for child in self.root.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            metadata_path = child / "metadata.json"
            if not metadata_path.is_file():
                continue
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            created_at = str(payload.get("created_at", ""))
            entries.append((created_at, child, _entry_byte_size(child)))
        entries.sort(key=lambda item: item[0])
        total_bytes = sum(size for _, _, size in entries)
        while entries and total_bytes > self.max_cache_bytes:
            _, entry_root, entry_size = entries.pop(0)
            shutil.rmtree(entry_root, ignore_errors=True)
            total_bytes -= entry_size

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
