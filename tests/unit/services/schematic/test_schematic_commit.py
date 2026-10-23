# In the name of God, the Most Gracious, the Most Merciful
"""Hash-guarded schematic saves and the ERC split on one commit."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ContentConflictError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services._internals import schematic_commit

if TYPE_CHECKING:
    from pathlib import Path


def test_place_and_wire_save_commits_once_and_splits_findings(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    calls: list[Path] = []
    real_commit = schematic_commit.commit_file

    def counting_commit(path: Path, *, expected_hash: str, content: bytes) -> str:
        calls.append(path)
        return real_commit(path, expected_hash=expected_hash, content=content)

    schematic_commit.commit_file = counting_commit
    try:
        created = server.invoke_tool("create_schematic", output_path="batch.qsch", overwrite=True)
        assert created["prior_findings"] == []
        added = server.invoke_tool(
            "add_component",
            schematic_path="batch.qsch",
            component_kind="resistor",
            reference="R1",
            value="1k",
        )
    finally:
        schematic_commit.commit_file = real_commit

    assert len(calls) == 1
    assert added["content_sha256"]
    introduced = {item["code"] for item in added["introduced_findings"]}
    prior = {item["code"] for item in added["prior_findings"]}
    assert "missing_ground" in introduced
    assert "missing_ground" not in prior
    assert all("fixable" in item and "location" in item for item in added["introduced_findings"])


def test_stale_hash_writes_nothing(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    created = server.invoke_tool("create_schematic", output_path="guard.qsch", overwrite=True)
    path = tmp_path / "guard.qsch"
    original = path.read_bytes()
    mutated = original.replace(b"schematic", b"schematiX", 1)
    assert mutated != original
    path.write_bytes(mutated)

    with pytest.raises(ContentConflictError):
        server.invoke_tool(
            "add_component",
            schematic_path="guard.qsch",
            component_kind="resistor",
            reference="R1",
            value="1k",
            expected_hash=str(created["content_sha256"]),
        )

    assert path.read_bytes() == mutated
