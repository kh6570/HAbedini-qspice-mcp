# In the name of God, the Most Gracious, the Most Merciful
"""MCP regressions for net renames and cross-workspace inspection."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import TYPE_CHECKING

import pytest
from mcp.shared.exceptions import McpError

from qspice_mcp.core.exceptions import ArtifactMissingError, SandboxViolationError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry
from qspice_mcp.mcp.tools import schematic as schematic_tools
from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic

if TYPE_CHECKING:
    from pathlib import Path


def test_net_rename_is_available_through_mcp_with_workspace_override(tmp_path: Path) -> None:
    client_root = tmp_path / "circuits"
    schematic = client_root / "input.qsch"
    create_starter_schematic(schematic, workspace_root=client_root, input_net_name="in")
    runtime = QSpiceToolRuntime(
        QSpiceSettings(workspace_root=tmp_path / "server"),
        build_runtime_tool_registry(),
    )
    result = runtime.invoke(
        "rename_net",
        schematic_path="input.qsch",
        workspace_root=str(client_root),
        net_name="in",
        new_net_name="vbus",
    )
    assert result["labels_renamed"] == 1
    assert result["wires_renamed"] == 1
    assert result["trace_id"]
    inspection = runtime.invoke(
        "inspect_schematic",
        schematic_path=str(schematic),
        workspace_root=str(client_root),
        include_connectivity=True,
        include_parameters=True,
    )
    assert inspection["connectivity"] is not None
    assert runtime.settings.workspace_root == (tmp_path / "server").resolve()


def test_explicit_root_bounds_absolute_inspection_path(tmp_path: Path) -> None:
    server_root = tmp_path / "server"
    client_root = tmp_path / "client"
    schematic = client_root / "input.qsch"
    create_starter_schematic(schematic, workspace_root=client_root)
    runtime = QSpiceToolRuntime(
        QSpiceSettings(workspace_root=server_root),
        build_runtime_tool_registry(),
    )
    with pytest.raises(SandboxViolationError) as error:
        runtime.invoke(
            "inspect_schematic", schematic_path=str(schematic), workspace_root=str(server_root)
        )
    assert f"Active workspace root: {server_root.resolve()}" in str(error.value)
    assert "pass workspace_root explicitly" in str(error.value)
    result = runtime.invoke(
        "inspect_schematic",
        schematic_path="input.qsch",
        workspace_root=str(client_root),
        include_connectivity=True,
        include_parameters=True,
    )
    assert result["schematic_path"] == str(schematic.resolve())
    assert result["component_count"] == 2
    assert result["connectivity"] is not None


def test_absolute_inspection_infers_containing_folder_for_one_call(tmp_path: Path) -> None:
    server_root = tmp_path / "server"
    client_root = tmp_path / "client" / "circuits with spaces"
    schematic = client_root / "input.qsch"
    create_starter_schematic(schematic, workspace_root=client_root)
    runtime = QSpiceToolRuntime(
        QSpiceSettings(workspace_root=server_root), build_runtime_tool_registry()
    )

    result = runtime.invoke(
        "inspect_schematic",
        schematic_path=str(schematic),
        include_connectivity=True,
        include_parameters=True,
    )
    assert result["schematic_path"] == str(schematic.resolve())
    assert result["component_count"] == 2
    assert result["connectivity"] is not None
    assert runtime.settings.workspace_root == server_root.resolve()
    with pytest.raises(ArtifactMissingError):
        runtime.invoke("inspect_schematic", schematic_path="input.qsch")
    with pytest.raises(SandboxViolationError):
        runtime.invoke(
            "rename_net", schematic_path=str(schematic), net_name="VIN", new_net_name="vbus"
        )


def test_missing_absolute_inspection_file_reports_missing_artifact(tmp_path: Path) -> None:
    runtime = QSpiceToolRuntime(
        QSpiceSettings(workspace_root=tmp_path / "server"), build_runtime_tool_registry()
    )
    with pytest.raises(ArtifactMissingError):
        runtime.invoke("inspect_schematic", schematic_path=str(tmp_path / "missing.qsch"))
    assert runtime.settings.workspace_root == (tmp_path / "server").resolve()


@pytest.mark.anyio
@pytest.mark.parametrize("configured_default", [False, True])
async def test_mcp_call_infers_root_but_respects_explicit_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, configured_default: bool
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    client_root = tmp_path / "client"
    schematic = client_root / "input.qsch"
    create_starter_schematic(schematic, workspace_root=client_root)
    settings = (
        QSpiceSettings(exe=executable)
        if configured_default
        else QSpiceSettings(exe=executable, workspace_root=tmp_path / "server")
    )
    server = create_server(settings)
    roots = []

    def capture_inspection(raw_path: str, *, workspace_root: Path, **kwargs: object):
        roots.append(workspace_root)
        return inspect_schematic(raw_path, workspace_root=workspace_root, **kwargs)

    async def advertised_root(context: object) -> Path:
        del context
        return tmp_path / "advertised"

    monkeypatch.setattr(schematic_tools, "inspect_schematic_service", capture_inspection)
    monkeypatch.setattr(server.app, "_resolve_advertised_root", advertised_root)
    await server.app.call_tool(
        "inspect_schematic", {"schematic_path": str(schematic), "include_connectivity": True}
    )
    assert roots == [client_root.resolve()]
    with pytest.raises(McpError) as error:
        await server.app.call_tool(
            "inspect_schematic",
            {"schematic_path": str(schematic), "workspace_root": str(tmp_path / "explicit")},
        )
    assert error.value.error.data["error_code"] == "sandbox_violation"
    assert roots[-1] == (tmp_path / "explicit").resolve()


def test_concurrent_inferred_inspection_roots_are_isolated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    server_root = tmp_path / "server"
    roots = [tmp_path / "first", tmp_path / "second"]
    for root in roots:
        create_starter_schematic(root / "input.qsch", workspace_root=root)
    runtime = QSpiceToolRuntime(
        QSpiceSettings(workspace_root=server_root), build_runtime_tool_registry()
    )
    barrier = Barrier(2)

    def capture_inspection(raw_path: str, *, workspace_root: Path, **kwargs: object):
        barrier.wait(timeout=10)
        assert runtime.settings.workspace_root == workspace_root
        return inspect_schematic(raw_path, workspace_root=workspace_root, **kwargs)

    monkeypatch.setattr(schematic_tools, "inspect_schematic_service", capture_inspection)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                runtime.invoke, "inspect_schematic", schematic_path=str(root / "input.qsch")
            )
            for root in roots
        ]
        results = [future.result(timeout=20) for future in futures]
    assert [result["schematic_path"] for result in results] == [
        str((root / "input.qsch").resolve()) for root in roots
    ]
    assert runtime.settings.workspace_root == server_root.resolve()
