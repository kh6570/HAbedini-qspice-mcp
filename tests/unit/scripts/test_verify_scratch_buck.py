"""Tests for scripts/verify_scratch_buck.py."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server


def test_verify_scratch_buck_topology_smoke(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    preflight = server.invoke_tool("describe_topology_authoring_support")
    assert preflight["scratch_buck_ready"] is True

    created = server.invoke_tool(
        "create_schematic",
        output_path="scratch_buck_verify.qsch",
        overwrite=True,
    )
    schematic_name = Path(str(created["output_path"])).name
    server.invoke_tool(
        "add_component",
        schematic_path=schematic_name,
        component_kind="inductor",
        reference="L1",
        value="50µ",
    )
    listed = server.invoke_tool("list_components", schematic_path=schematic_name)
    references = {item["reference"] for item in listed["components"]}
    assert "L1" in references
