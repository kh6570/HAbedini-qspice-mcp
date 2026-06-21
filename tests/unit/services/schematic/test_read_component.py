"""Tests for the read_component service."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.read_component import read_component

component_service = importlib.import_module("qspice_mcp.services.schematic.read_component")


def _supported_subcircuit_schematic_bytes() -> bytes:
    return b"".join(
        (
            b"\xff\xd8\xff\xdb",
            b"\xabschematic\r\n",
            b"  \xabcomponent (400,400) 0 0\r\n",
            b"    \xabsymbol X\r\n",
            b"      \xabtype: X\xbb\r\n",
            b"      \xabdescription: Comparator\xbb\r\n",
            b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "X1"\xbb\r\n',
            b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "COMPARATOR"\xbb\r\n',
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "INP"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "OUT"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"\xbb\r\n\r\n",
        )
    )


def _supported_leaf_subcircuit_definition_bytes() -> bytes:
    return b"".join(
        (
            b"\xff\xd8\xff\xdb",
            b"\xabschematic\r\n",
            b"  \xabcomponent (400,400) 0 0\r\n",
            b"    \xabsymbol R\r\n",
            b"      \xabtype: R\xbb\r\n",
            b"      \xabdescription: Feedback resistor\xbb\r\n",
            b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n',
            b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "2k"\xbb\r\n',
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "1"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "2"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"\xbb\r\n\r\n",
        )
    )


def _supported_nested_subcircuit_definition_bytes() -> bytes:
    return b"".join(
        (
            b"\xff\xd8\xff\xdb",
            b"\xabschematic\r\n",
            b"  \xabcomponent (400,400) 0 0\r\n",
            b"    \xabsymbol X\r\n",
            b"      \xabtype: X\xbb\r\n",
            b"      \xabdescription: Nested Filter\xbb\r\n",
            b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "X2"\xbb\r\n',
            b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "FILTER"\xbb\r\n',
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "INP"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "OUT"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"\xbb\r\n\r\n",
        )
    )


@dataclass
class FakePoint:
    X: int
    Y: int


@dataclass
class FakeComponent:
    reference: str
    attributes: dict[str, object]
    ports: tuple[str, ...]


class FakeEditor:
    def __init__(self) -> None:
        self._component = FakeComponent(
            reference="X1:R1",
            attributes={
                "type": "R",
                "value": "2k",
                "description": "Feedback resistor",
                "_SUBCKT": object(),
            },
            ports=("OUT", "FB"),
        )

    def get_component(self, reference: str) -> FakeComponent:
        assert reference == "X1:R1"
        return self._component

    def get_component_parameters(self, element: str) -> dict[object, object]:
        assert element == "X1:R1"
        return {"Tc1": "100ppm", 2: "tol=1%", "temp": "25"}

    def get_component_nodes(self, reference: str) -> tuple[str, ...]:
        assert reference == "X1:R1"
        return self._component.ports

    def get_component_position(self, reference: str) -> tuple[object, object]:
        assert reference == "X1:R1"
        return FakePoint(1200, -300), 2


def test_read_component_reads_capital_value_from_editor_parameters(
    monkeypatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    class VoltageEditor(FakeEditor):
        def __init__(self) -> None:
            self._component = FakeComponent(
                reference="V1",
                attributes={"type": "V", "description": "Independent Voltage Source"},
                ports=("N01", "0"),
            )

        def get_component(self, reference: str) -> FakeComponent:
            assert reference == "V1"
            return self._component

        def get_component_parameters(self, element: str) -> dict[object, object]:
            assert element == "V1"
            return {"Value": "10"}

        def get_component_nodes(self, reference: str) -> tuple[str, ...]:
            assert reference == "V1"
            return self._component.ports

        def get_component_position(self, reference: str) -> tuple[object, object]:
            assert reference == "V1"
            return FakePoint(400, 400), 0

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            VoltageEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = read_component(schematic, workspace_root=tmp_path, reference="V1")

    assert result.reference == "V1"
    assert result.kind == "V"
    assert result.value == "10"


def test_read_component_normalizes_parameters_and_position(monkeypatch, tmp_path: Path) -> None:
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

    result = read_component(schematic, workspace_root=tmp_path, reference="X1:R1")

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.reference == "X1:R1"
    assert result.kind == "R"
    assert result.value == "2k"
    assert result.description == "Feedback resistor"
    assert result.nodes == ("OUT", "FB")
    assert result.parameters == {"Tc1": "100ppm", "temp": "25"}
    assert result.raw_parameter_lines == ("tol=1%",)
    assert result.position_x == 1200
    assert result.position_y == -300
    assert result.rotation_degrees == 90
    assert result.has_subcircuit is True


def test_read_component_falls_back_to_supported_clean_room_subset(
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

    result = read_component(schematic, workspace_root=tmp_path, reference="V1")

    assert result.reference == "V1"
    assert result.kind == "V"
    assert result.value == "10"
    assert result.description == "Independent Voltage Source"
    assert result.nodes == ("VIN", "0")
    assert result.parameters == {}
    assert result.raw_parameter_lines == ()
    assert result.position_x == 400
    assert result.position_y == 400
    assert result.rotation_degrees == 0
    assert result.has_subcircuit is False


def test_read_component_falls_back_to_external_subcircuit_component_without_backend(
    monkeypatch: pytest.MonkeyPatch,  # noqa: F821
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (_ for _ in ()).throw(
            BackendUnavailableError("QschEditor is unavailable.")
        ),
    )

    result = read_component(schematic, workspace_root=tmp_path, reference="X1:R1")

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.reference == "X1:R1"
    assert result.kind == "R"
    assert result.value == "2k"
    assert result.description == "Feedback resistor"
    assert result.nodes == ("N001", "N002")
    assert result.parameters == {}
    assert result.raw_parameter_lines == ()
    assert result.position_x == 400
    assert result.position_y == 400
    assert result.rotation_degrees == 0
    assert result.has_subcircuit is False


def test_read_component_falls_back_to_nested_external_subcircuit_component_without_backend(
    monkeypatch: pytest.MonkeyPatch,  # noqa: F821
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_nested_subcircuit_definition_bytes())
    (tmp_path / "FILTER.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    monkeypatch.setattr(
        component_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (_ for _ in ()).throw(
            BackendUnavailableError("QschEditor is unavailable.")
        ),
    )

    result = read_component(schematic, workspace_root=tmp_path, reference="X1:X2:R1")

    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.reference == "X1:X2:R1"
    assert result.kind == "R"
    assert result.value == "2k"
    assert result.description == "Feedback resistor"
    assert result.nodes == ("N001", "N002")
    assert result.position_x == 400
    assert result.position_y == 400
    assert result.rotation_degrees == 0
    assert result.has_subcircuit is False
