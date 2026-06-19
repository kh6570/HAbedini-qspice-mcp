"""Tests for simulation artifact cache keying."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.services._internals.simulation_cache import SimulationArtifactCache


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
