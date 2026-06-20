"""Tests for library include authoring."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.simulation._analysis_directive import append_lines_before_end
from qspice_mcp.services.simulation.add_library_include import add_library_include

if TYPE_CHECKING:
    from pathlib import Path


def test_append_lines_before_end_inserts_multiple_lines(tmp_path: Path) -> None:
    netlist = tmp_path / "top.net"
    netlist.write_text("* top\n.end\n", encoding="utf-8")

    append_lines_before_end(netlist, (".include models/a.lib", ".include models/b.lib"))

    updated = netlist.read_text(encoding="utf-8")
    assert ".include models/a.lib" in updated
    assert ".include models/b.lib" in updated
    assert updated.index(".include models/a.lib") < updated.index(".end")


def test_add_library_include_appends_directive(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    library = models / "devices.lib"
    library.write_text("* library\n.end\n", encoding="utf-8")
    netlist = tmp_path / "amp.net"
    netlist.write_text("* amp\n.end\n", encoding="utf-8")

    result = add_library_include(
        netlist,
        workspace_root=tmp_path,
        include_path=library,
    )

    updated = result.output_netlist.read_text(encoding="utf-8")
    assert ".include models/devices.lib" in updated
    assert result.directive == ".include models/devices.lib"


def test_add_library_include_rejects_duplicate(tmp_path: Path) -> None:
    models = tmp_path / "models"
    models.mkdir()
    library = models / "devices.lib"
    library.write_text("* library\n.end\n", encoding="utf-8")
    netlist = tmp_path / "amp.net"
    netlist.write_text("* amp\n.include models/devices.lib\n.end\n", encoding="utf-8")

    with pytest.raises(ValidationError, match="already present"):
        add_library_include(
            netlist,
            workspace_root=tmp_path,
            include_path=library,
        )
