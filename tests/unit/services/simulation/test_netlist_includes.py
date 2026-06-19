"""Tests for netlist include discovery and cache keying."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_cache import SimulationArtifactCache
from qspice_mcp.services.simulation._netlist_includes import (
    collect_netlist_includes,
    hash_include_dependencies,
)
from qspice_mcp.services.simulation.list_includes import list_includes
from qspice_mcp.services.simulation.resolve_model_libraries import resolve_model_libraries

if TYPE_CHECKING:
    from pathlib import Path


def test_collect_netlist_includes_finds_nested_files(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    child = models / "child.inc"
    child.write_text("* child\n.end\n", encoding="utf-8")
    library = models / "devices.lib"
    library.write_text("* library\n.end\n", encoding="utf-8")
    root = tmp_path / "top.net"
    root.write_text(
        "\n".join(
            (
                "* top",
                ".include models/child.inc",
                ".lib models/devices.lib",
                ".end",
            )
        ),
        encoding="utf-8",
    )

    includes = collect_netlist_includes(root, workspace_root=tmp_path)

    assert len(includes) == 2
    assert all(entry.exists for entry in includes)


def test_build_key_changes_when_include_content_changes(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    included = models / "child.inc"
    included.write_text("* v1\n.end\n", encoding="utf-8")
    netlist = tmp_path / "top.net"
    netlist.write_text("* top\n.include models/child.inc\n.end\n", encoding="utf-8")
    cache = SimulationArtifactCache(tmp_path / "cache")

    base_kwargs = {
        "netlist_path": netlist,
        "adapter_key": "cli.v1",
        "executable": str(tmp_path / "QSPICE64.exe"),
        "executable_version": "1.0.0.0",
        "executable_mtime": 1.0,
        "extra_switches": (),
        "ascii_raw": False,
    }
    includes = collect_netlist_includes(netlist, workspace_root=tmp_path)
    key_v1 = cache.build_key(
        **base_kwargs,
        include_hashes=hash_include_dependencies(includes),
    )
    included.write_text("* v2\n.end\n", encoding="utf-8")
    includes_v2 = collect_netlist_includes(netlist, workspace_root=tmp_path)
    key_v2 = cache.build_key(
        **base_kwargs,
        include_hashes=hash_include_dependencies(includes_v2),
    )

    assert key_v1 != key_v2


def test_list_includes_and_resolve_model_libraries(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    library = models / "devices.lib"
    library.write_text("* library\n.end\n", encoding="utf-8")
    netlist = tmp_path / "amp.net"
    netlist.write_text("* amp\n.lib models/devices.lib\n.end\n", encoding="utf-8")

    catalog = list_includes(netlist, workspace_root=tmp_path)
    resolution = resolve_model_libraries(netlist, workspace_root=tmp_path)

    assert catalog.include_count == 1
    assert catalog.missing_count == 0
    assert resolution.library_count == 1
    assert resolution.missing_count == 0
