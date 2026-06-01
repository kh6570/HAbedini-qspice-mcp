"""Tests for plot-suggestion extraction."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.services.simulation.generate_netlist import GeneratedNetlist
from qspice_mcp.services.simulation.list_plot_suggestions import list_plot_suggestions

plot_module = importlib.import_module("qspice_mcp.services.simulation.list_plot_suggestions")


def test_list_plot_suggestions_reads_plot_and_abscissa_directives(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.net"
    netlist.write_text(
        "* example\n"
        ".plot tran V(out) I(R1)\n"
        ".abscissa V(in)\n"
        ".probe ac DB(V(out)) PH(V(out))\n"
        "+ MAG(I(L1))\n",
        encoding="utf-8",
    )

    result = list_plot_suggestions(netlist, workspace_root=tmp_path)

    assert result.source_kind == "netlist"
    assert result.abscissa_expression == "V(in)"
    assert len(result.suggestions) == 2
    assert result.suggestions[0].analysis == "TRAN"
    assert result.suggestions[0].expressions == ("V(out)", "I(R1)")
    assert result.suggestions[1].analysis == "AC"
    assert result.suggestions[1].expressions[-1] == "MAG(I(L1))"


def test_list_plot_suggestions_can_stage_schematic_netlist(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    derived = tmp_path / "demo.net"
    derived.write_text(".plot tran V(out)\n", encoding="utf-8")

    monkeypatch.setattr(
        plot_module,
        "generate_netlist_service",
        lambda source_path, *, workspace_root, output_path=None: GeneratedNetlist(
            source_path=Path(source_path).resolve(strict=False),
            netlist_path=derived.resolve(strict=False),
            source_kind="schematic",
            refreshed=False,
            copied=False,
            warnings=("used staged netlist",),
        ),
    )

    result = list_plot_suggestions(schematic, workspace_root=tmp_path)

    assert result.source_kind == "schematic"
    assert result.netlist_path == derived.resolve(strict=False)
    assert result.warnings == ("used staged netlist",)
    assert result.suggestions[0].directive == ".plot tran V(out)"
