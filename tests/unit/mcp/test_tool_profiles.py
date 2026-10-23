# In the name of God, the Most Gracious, the Most Merciful
"""Default sessions hide extended tool groups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.mcp.tool_registry import build_tool_registry

if TYPE_CHECKING:
    from pathlib import Path

_EXTENDED = {
    "submit_batch",
    "submit_remote_simulation",
    "launch_live_gui_session",
    "ingest_topology_contribution",
}
_DEFAULT = {"add_component", "run_simulation", "measure_waveform", "check_schematic"}


def test_default_session_hides_extended_groups(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    names = {tool.name for tool in server.registered_tools}

    assert names >= _DEFAULT
    assert names.isdisjoint(_EXTENDED)
    described = server.invoke_tool("describe_server_capabilities")
    hidden = {group["name"]: group for group in described["hidden_tool_groups"]}
    assert set(hidden) == {"batch", "remote", "live_gui", "topology_ingest"}
    assert "submit_remote_simulation" in hidden["remote"]["tools"]
    assert "QSPICE_TOOL_PROFILES=default,extended" in hidden["batch"]["enable"]


def test_extended_profile_loads_hidden_groups(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            tool_profiles="default,extended",
        )
    )
    names = {tool.name for tool in server.registered_tools}
    assert names >= _EXTENDED
    assert len(build_tool_registry()) >= len(names)
    described = server.invoke_tool("describe_server_capabilities")
    assert described["hidden_tool_groups"] == []
