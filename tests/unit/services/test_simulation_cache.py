"""Tests for simulation artifact cache keying."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.persistence_schema import stamp_schema_version
from qspice_mcp.services._internals.simulation_cache import SimulationArtifactCache

if TYPE_CHECKING:
    from pathlib import Path


def test_build_key_changes_when_executable_version_changes(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    cache = SimulationArtifactCache(tmp_path / "cache")

    base_kwargs = {
        "netlist_path": netlist,
        "adapter_key": "cli.v1",
        "executable": str(tmp_path / "QSPICE64.exe"),
        "extra_switches": (),
        "ascii_raw": False,
    }
    key_v1 = cache.build_key(**base_kwargs, executable_version="1.0.0.0", executable_mtime=1.0)
    key_v2 = cache.build_key(**base_kwargs, executable_version="2.0.0.0", executable_mtime=1.0)

    assert key_v1 != key_v2


def test_build_key_changes_when_executable_mtime_changes(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")
    cache = SimulationArtifactCache(tmp_path / "cache")

    base_kwargs = {
        "netlist_path": netlist,
        "adapter_key": "cli.v1",
        "executable": str(tmp_path / "QSPICE64.exe"),
        "executable_version": "1.0.0.0",
        "extra_switches": (),
        "ascii_raw": False,
    }
    key_old = cache.build_key(**base_kwargs, executable_mtime=1.0)
    key_new = cache.build_key(**base_kwargs, executable_mtime=2.0)

    assert key_old != key_new


def test_put_and_get_round_trip_with_integrity(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = SimulationArtifactCache(cache_root)
    log_source = tmp_path / "run.log"
    raw_source = tmp_path / "run.qraw"
    log_source.write_text("log", encoding="utf-8")
    raw_source.write_bytes(b"raw")

    entry = cache.put(
        "abc123",
        log_source=log_source,
        raw_source=raw_source,
        exit_code=0,
        duration_s=1.5,
        stdout="ok",
        stderr="",
    )

    loaded = cache.get("abc123")
    assert loaded is not None
    assert loaded.key == entry.key
    assert loaded.stdout == "ok"
    assert loaded.log_path.read_text(encoding="utf-8") == "log"
    assert loaded.raw_path.read_bytes() == b"raw"
    assert (cache_root / "abc123" / "metadata.json").is_file()


def test_get_invalidates_when_integrity_hash_mismatch(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = SimulationArtifactCache(cache_root)
    key = "deadbeef"
    entry_root = cache_root / key
    entry_root.mkdir(parents=True)
    log_path = entry_root / "artifacts.log"
    raw_path = entry_root / "artifacts.qraw"
    log_path.write_text("log", encoding="utf-8")
    raw_path.write_bytes(b"raw")
    metadata = stamp_schema_version(
        {
            "created_at": "2026-01-01T00:00:00+00:00",
            "duration_s": None,
            "exit_code": 0,
            "integrity_hash": "0" * 64,
            "stdout": "",
            "stderr": "",
        }
    )
    (entry_root / "metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    assert cache.get(key) is None
    assert not entry_root.exists()


def test_eviction_removes_oldest_entries_when_over_budget(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    cache = SimulationArtifactCache(cache_root, max_cache_bytes=450)
    log_source = tmp_path / "run.log"
    raw_source = tmp_path / "run.qraw"
    log_source.write_text("x" * 80, encoding="utf-8")
    raw_source.write_bytes(b"y" * 80)

    cache.put(
        "first",
        log_source=log_source,
        raw_source=raw_source,
        exit_code=0,
        duration_s=1.0,
        stdout="",
        stderr="",
    )
    time.sleep(0.02)
    cache.put(
        "second",
        log_source=log_source,
        raw_source=raw_source,
        exit_code=0,
        duration_s=1.0,
        stdout="",
        stderr="",
    )

    assert cache.get("first") is None
    assert cache.get("second") is not None
