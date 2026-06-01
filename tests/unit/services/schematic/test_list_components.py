"""Tests for the list_components service."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.list_components import list_components

component_service = importlib.import_module("qspice_mcp.services.schematic.list_components")


@dataclass
class FakeComponent:
    reference: str
    attributes: dict[str, object]
    ports: tuple[str, ...]


class FakeEditor:
    def __init__(self) -> None:
        self._components = {
            "R1": FakeComponent(
                reference="R1",
                attributes={"type": "R", "value": "1k", "description": "Resistor"},
                ports=("N001", "N002"),
            ),
            "X1": FakeComponent(
                reference="X1",
                attributes={
                    "type": "X",
                    "value": "amp",
                    "description": "Subcircuit",
                    "_SUBCKT": object(),
                },
                ports=("IN", "OUT", "V+", "V-"),
            ),
        }

    def get_components(self, prefixes: str = "*") -> list[str]:
        if prefixes == "*":
            return ["R1", "X1"]
        return [reference for reference in ("R1", "X1") if reference[0] in prefixes]

    def get_component(self, reference: str) -> FakeComponent:
        return self._components[reference]


def test_list_components_normalizes_editor_metadata(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = list_components(schematic, workspace_root=tmp_path)

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.component_count == 2
    assert result.prefixes == "*"
    assert result.components[0].reference == "R1"
    assert result.components[0].kind == "R"
    assert result.components[0].value == "1k"
    assert result.components[0].node_count == 2
    assert result.components[1].has_subcircuit is True


def test_list_components_applies_prefix_filter(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = list_components(schematic, workspace_root=tmp_path, prefixes="R")

    assert result.component_count == 1
    assert tuple(component.reference for component in result.components) == ("R1",)


def test_list_components_falls_back_to_supported_clean_room_subset(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "starter.qsch"
    create_starter_schematic(schematic, workspace_root=tmp_path)

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (_ for _ in ()).throw(
            BackendUnavailableError("QschEditor is unavailable.")
        ),
    )

    result = list_components(schematic, workspace_root=tmp_path, prefixes="R")

    assert result.component_count == 1
    assert result.components == (
        component_service.ComponentSummary(
            reference="R1",
            kind="R",
            value="1k",
            description="Resistor(USA Style Symbol)",
            node_count=2,
            has_subcircuit=False,
        ),
    )


def test_list_components_returns_empty_catalog_for_blank_clean_room_schematic(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "blank.qsch"
    create_schematic(schematic, workspace_root=tmp_path)

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (_ for _ in ()).throw(
            BackendUnavailableError("QschEditor is unavailable.")
        ),
    )

    result = list_components(schematic, workspace_root=tmp_path)

    assert result.component_count == 0
    assert result.components == ()
