"""Tests for subcircuit inspection and edit services."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

import pytest
from tests.support.subcircuit_fixtures import (
    supported_leaf_subcircuit_definition_bytes as _supported_leaf_subcircuit_definition_bytes,
)
from tests.support.subcircuit_fixtures import (
    supported_subcircuit_schematic_bytes as _supported_subcircuit_schematic_bytes,
)

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services.subcircuit.list_subcircuits import list_subcircuits
from qspice_mcp.services.subcircuit.read_subcircuit import read_subcircuit
from qspice_mcp.services.subcircuit.set_subcircuit_component_parameters import (
    set_subcircuit_component_parameters,
)
from qspice_mcp.services.subcircuit.set_subcircuit_component_value import (
    set_subcircuit_component_value,
)

list_subcircuits_service = importlib.import_module(
    "qspice_mcp.services.subcircuit.list_subcircuits"
)
read_subcircuit_service = importlib.import_module("qspice_mcp.services.subcircuit.read_subcircuit")
set_subcircuit_component_value_service = importlib.import_module(
    "qspice_mcp.services.subcircuit.set_subcircuit_component_value"
)
set_subcircuit_component_parameters_service = importlib.import_module(
    "qspice_mcp.services.subcircuit.set_subcircuit_component_parameters"
)


def _supported_nested_subcircuit_definition_bytes(
    *,
    nested_reference: str = "X2",
    nested_definition_name: str = "FILTER",
) -> bytes:
    return b"".join(
        (
            b"\xff\xd8\xff\xdb",
            b"\xabschematic\r\n",
            b"  \xabcomponent (400,400) 0 0\r\n",
            b"    \xabsymbol X\r\n",
            b"      \xabtype: X\xbb\r\n",
            b"      \xabdescription: Nested Filter\xbb\r\n",
            f'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "{nested_reference}"\xbb\r\n'.encode(
                "latin-1"
            ),
            (
                f"      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "
                f'"{nested_definition_name}"\xbb\r\n'
            ).encode("latin-1"),
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "INP"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "OUT"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"  \xabcomponent (800,400) 0 0\r\n",
            b"    \xabsymbol R\r\n",
            b"      \xabtype: R\xbb\r\n",
            b"      \xabdescription: Bias\xbb\r\n",
            b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n',
            b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "10k"\xbb\r\n',
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "1"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "2"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"\xbb\r\n\r\n",
        )
    )


@dataclass
class FakeComponent:
    reference: str
    attributes: dict[str, object]
    ports: tuple[str, ...]


class FakeSubcircuitEditor:
    def __init__(self, *, nested: dict[str, FakeSubcircuitEditor] | None = None) -> None:
        self.calls: list[tuple[str, object]] = []
        self._nested = nested or {}
        self._components = {
            "R1": FakeComponent(
                "R1", {"type": "R", "value": "2k", "description": "Feedback"}, ("OUT", "FB")
            ),
            "C1": FakeComponent(
                "C1", {"type": "C", "value": "10p", "description": "Comp"}, ("FB", "0")
            ),
        }
        for reference in self._nested:
            self._components.setdefault(
                reference,
                FakeComponent(
                    reference,
                    {
                        "type": "X",
                        "value": f"{reference}_BLOCK",
                        "description": f"Nested {reference}",
                    },
                    ("IN", "OUT"),
                ),
            )

    def get_components(self, prefixes: str = "*") -> tuple[str, ...]:
        if prefixes == "*":
            return tuple(self._components)
        return tuple(
            reference for reference in self._components if reference.startswith(tuple(prefixes))
        )

    def get_component(self, reference: str) -> FakeComponent:
        return self._components[reference]

    def get_subcircuit(self, reference: str) -> FakeSubcircuitEditor:
        try:
            return self._nested[reference]
        except KeyError as exc:
            raise AttributeError(f"missing nested subcircuit: {reference}") from exc

    def set_component_value(self, reference: str, value: object) -> None:
        self.calls.append(("set_component_value", (reference, value)))

    def set_component_parameters(self, reference: str, **kwargs: object) -> None:
        self.calls.append(("set_component_parameters", (reference, kwargs)))

    def save_as(self, destination: str | Path) -> None:
        Path(destination).write_text("subckt\n", encoding="utf-8")


class FakeTopEditor:
    def __init__(self, subeditor: FakeSubcircuitEditor, *, resolvable: bool = True) -> None:
        self.calls: list[tuple[str, object]] = []
        self.subeditor = subeditor
        self.resolvable = resolvable
        self._component = FakeComponent(
            "X1",
            {"type": "X", "value": "COMPARATOR", "description": "Comparator"},
            ("INP", "INM", "OUT"),
        )

    def get_components(self, prefixes: str = "*") -> tuple[str, ...]:
        assert prefixes == "X"
        return ("X1",)

    def get_component(self, reference: str) -> FakeComponent:
        assert reference == "X1"
        return self._component

    def get_subcircuit(self, reference: str) -> FakeSubcircuitEditor:
        assert reference == "X1"
        if not self.resolvable:
            raise AttributeError("missing subcircuit")
        return self.subeditor

    def set_component_value(self, reference: str, value: object) -> None:
        self.calls.append(("set_component_value", (reference, value)))

    def set_component_parameters(self, reference: str, **kwargs: object) -> None:
        self.calls.append(("set_component_parameters", (reference, kwargs)))

    def save_as(self, destination: str | Path) -> None:
        Path(destination).write_text("top\n", encoding="utf-8")


def test_list_subcircuits_reports_resolution_errors(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    subeditor = FakeSubcircuitEditor()

    monkeypatch.setattr(
        list_subcircuits_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor, resolvable=False),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = list_subcircuits(schematic, workspace_root=tmp_path)

    assert result.subcircuit_count == 1
    assert result.subcircuits[0].reference == "X1"
    assert result.subcircuits[0].definition_available is False
    assert result.subcircuits[0].definition_resolution_error == "missing subcircuit"
    assert result.instance_path == ()


def test_list_subcircuits_falls_back_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())

    def fail_open(*args: object, **kwargs: object) -> tuple[object, Path, str]:
        del args, kwargs
        raise BackendUnavailableError("missing backend")

    monkeypatch.setattr(list_subcircuits_service, "open_schematic_editor", fail_open)

    result = list_subcircuits(schematic, workspace_root=tmp_path)

    assert result.subcircuit_count == 1
    assert result.subcircuits[0].reference == "X1"
    assert result.subcircuits[0].definition_name == "COMPARATOR"
    assert result.subcircuits[0].definition_available is False
    assert result.subcircuits[0].component_count is None
    assert "File not found" in (result.subcircuits[0].definition_resolution_error or "")


def test_list_subcircuits_falls_back_to_external_qsch_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    def fail_open(*args: object, **kwargs: object) -> tuple[object, Path, str]:
        del args, kwargs
        raise BackendUnavailableError("missing backend")

    monkeypatch.setattr(list_subcircuits_service, "open_schematic_editor", fail_open)

    result = list_subcircuits(schematic, workspace_root=tmp_path)

    assert result.subcircuit_count == 1
    assert result.subcircuits[0].reference == "X1"
    assert result.subcircuits[0].definition_available is True
    assert result.subcircuits[0].component_count == 2


def test_list_subcircuits_nested_fallback_resolves_external_qsch_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_nested_subcircuit_definition_bytes())
    (tmp_path / "FILTER.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    def fail_open(*args: object, **kwargs: object) -> tuple[object, Path, str]:
        del args, kwargs
        raise BackendUnavailableError("missing backend")

    monkeypatch.setattr(list_subcircuits_service, "open_schematic_editor", fail_open)

    result = list_subcircuits(schematic, workspace_root=tmp_path, instance_path=["X1"])

    assert result.instance_path == ("X1",)
    assert result.subcircuit_count == 1
    assert result.subcircuits[0].reference == "X2"
    assert result.subcircuits[0].definition_name == "FILTER"
    assert result.subcircuits[0].definition_available is True
    assert result.subcircuits[0].component_count == 2


def test_read_subcircuit_returns_nested_components(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    subeditor = FakeSubcircuitEditor()

    monkeypatch.setattr(
        read_subcircuit_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = read_subcircuit(schematic, workspace_root=tmp_path, reference="X1", scope="definition")

    assert result.reference == "X1"
    assert result.instance_path == ()
    assert result.scope == "definition"
    assert result.definition_name == "COMPARATOR"
    assert result.component_count == 2
    assert result.components[0].reference == "R1"


def test_read_subcircuit_falls_back_to_external_qsch_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    def fail_open(*args: object, **kwargs: object) -> tuple[object, Path, str]:
        del args, kwargs
        raise BackendUnavailableError("missing backend")

    monkeypatch.setattr(read_subcircuit_service, "open_schematic_editor", fail_open)

    result = read_subcircuit(schematic, workspace_root=tmp_path, reference="X1", scope="definition")

    assert result.reference == "X1"
    assert result.instance_path == ()
    assert result.scope == "definition"
    assert result.definition_name == "COMPARATOR"
    assert result.component_count == 2
    assert tuple(component.reference for component in result.components) == ("R1", "C1")
    assert "clean-room external .qsch lookup" in result.warnings[0]


def test_list_subcircuits_can_anchor_to_nested_instance_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    nested_editor = FakeSubcircuitEditor()
    subeditor = FakeSubcircuitEditor(nested={"X2": nested_editor})

    monkeypatch.setattr(
        list_subcircuits_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = list_subcircuits(
        schematic,
        workspace_root=tmp_path,
        instance_path=["X1"],
    )

    assert result.instance_path == ("X1",)
    assert result.subcircuit_count == 1
    assert result.subcircuits[0].reference == "X2"


def test_read_subcircuit_can_resolve_nested_instance_path(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    nested_editor = FakeSubcircuitEditor()
    subeditor = FakeSubcircuitEditor(nested={"X2": nested_editor})

    monkeypatch.setattr(
        read_subcircuit_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = read_subcircuit(
        schematic,
        workspace_root=tmp_path,
        reference="X2",
        instance_path=["X1"],
    )

    assert result.instance_path == ("X1",)
    assert result.reference == "X2"
    assert result.component_count == 2


def test_read_subcircuit_can_resolve_nested_instance_path_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(_supported_subcircuit_schematic_bytes())
    (tmp_path / "COMPARATOR.qsch").write_bytes(_supported_nested_subcircuit_definition_bytes())
    (tmp_path / "FILTER.qsch").write_bytes(_supported_leaf_subcircuit_definition_bytes())

    def fail_open(*args: object, **kwargs: object) -> tuple[object, Path, str]:
        del args, kwargs
        raise BackendUnavailableError("missing backend")

    monkeypatch.setattr(read_subcircuit_service, "open_schematic_editor", fail_open)

    result = read_subcircuit(
        schematic,
        workspace_root=tmp_path,
        reference="X2",
        instance_path=["X1"],
    )

    assert result.instance_path == ("X1",)
    assert result.reference == "X2"
    assert result.definition_name == "FILTER"
    assert result.component_count == 2
    assert tuple(component.reference for component in result.components) == ("R1", "C1")


def test_set_subcircuit_component_value_instance_uses_hierarchical_reference(
    monkeypatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    subeditor = FakeSubcircuitEditor()
    top_editor = FakeTopEditor(subeditor)

    monkeypatch.setattr(
        set_subcircuit_component_value_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            top_editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = set_subcircuit_component_value(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        component_reference="R1",
        value="3k",
        scope="instance",
        output_path=output,
    )

    assert result.scope == "instance"
    assert result.instance_path == ()
    assert result.output_path == output.resolve(strict=False)
    assert top_editor.calls[0] == ("set_component_value", ("X1:R1", "3k"))


def test_set_subcircuit_component_parameters_definition_saves_subeditor(
    monkeypatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "definition.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    subeditor = FakeSubcircuitEditor()

    monkeypatch.setattr(
        set_subcircuit_component_parameters_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = set_subcircuit_component_parameters(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        component_reference="R1",
        parameters={"tol": "1%"},
        scope="definition",
        output_path=output,
    )

    assert result.scope == "definition"
    assert result.instance_path == ()
    assert result.output_path == output.resolve(strict=False)
    assert subeditor.calls[0] == ("set_component_parameters", ("R1", {"tol": "1%"}))


def test_nested_instance_scope_edit_uses_full_hierarchical_selector(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    nested_editor = FakeSubcircuitEditor()
    subeditor = FakeSubcircuitEditor(nested={"X2": nested_editor})
    top_editor = FakeTopEditor(subeditor)

    monkeypatch.setattr(
        set_subcircuit_component_value_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            top_editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = set_subcircuit_component_value(
        schematic,
        workspace_root=tmp_path,
        reference="X2",
        instance_path=["X1"],
        component_reference="R1",
        value="4k",
        scope="instance",
        output_path=output,
    )

    assert result.instance_path == ("X1",)
    assert top_editor.calls[0] == ("set_component_value", ("X1:X2:R1", "4k"))


def test_nested_definition_scope_uses_resolved_nested_editor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "definition.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    nested_editor = FakeSubcircuitEditor()
    subeditor = FakeSubcircuitEditor(nested={"X2": nested_editor})

    monkeypatch.setattr(
        set_subcircuit_component_parameters_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    result = set_subcircuit_component_parameters(
        schematic,
        workspace_root=tmp_path,
        reference="X2",
        instance_path=["X1"],
        component_reference="R1",
        parameters={"tol": "2%"},
        scope="definition",
        output_path=output,
    )

    assert result.instance_path == ("X1",)
    assert nested_editor.calls[0] == ("set_component_parameters", ("R1", {"tol": "2%"}))


def test_definition_scope_requires_explicit_output_path(monkeypatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    subeditor = FakeSubcircuitEditor()

    monkeypatch.setattr(
        set_subcircuit_component_value_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeTopEditor(subeditor),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )

    with pytest.raises(ValueError, match="output_path is required"):
        set_subcircuit_component_value(
            schematic,
            workspace_root=tmp_path,
            reference="X1",
            component_reference="R1",
            value="3k",
            scope="definition",
        )
