"""Tests for the explicit save_netlist_copy service."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.services.simulation.generate_netlist import GeneratedNetlist
from qspice_mcp.services.simulation.save_netlist_copy import save_netlist_copy

if TYPE_CHECKING:
    import pytest

save_netlist_copy_service = importlib.import_module(
    "qspice_mcp.services.simulation.save_netlist_copy"
)


def test_save_netlist_copy_delegates_to_generate_netlist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "demo.qsch"
    source.write_text("schematic", encoding="utf-8")
    output = tmp_path / "artifacts" / "demo-copy.net"

    def fake_generate_netlist(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
    ) -> GeneratedNetlist:
        assert Path(raw_path) == source.resolve(strict=False)
        assert workspace_root == tmp_path
        assert Path(output_path) == output
        return GeneratedNetlist(
            source_path=source.resolve(strict=False),
            netlist_path=output.resolve(strict=False),
            source_kind="schematic",
            refreshed=True,
            copied=True,
            warnings=("saved",),
        )

    monkeypatch.setattr(save_netlist_copy_service, "generate_netlist", fake_generate_netlist)

    result = save_netlist_copy(source, workspace_root=tmp_path, output_path=output)

    assert result.source_path == source.resolve(strict=False)
    assert result.output_path == output.resolve(strict=False)
    assert result.source_kind == "schematic"
    assert result.refreshed is True
    assert result.copied is True
    assert result.warnings == ("saved",)
