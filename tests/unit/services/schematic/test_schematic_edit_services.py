"""Tests for the QschEditor-backed schematic mutation services."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.clean_room_schematic import (
    blank_schematic_bytes,
    starter_schematic_bytes,
)
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.add_dll_block import add_dll_block
from qspice_mcp.services.schematic.add_instruction import add_instruction
from qspice_mcp.services.schematic.add_net_label import add_net_label
from qspice_mcp.services.schematic.add_wire import add_wire
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.create_starter_schematic import create_starter_schematic
from qspice_mcp.services.schematic.describe_edit_capability import (
    describe_edit_capability,
)
from qspice_mcp.services.schematic.describe_schematic_edit_support import (
    describe_schematic_edit_support,
)
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic
from qspice_mcp.services.schematic.remove_component import (
    remove_component,
)
from qspice_mcp.services.schematic.remove_instruction import remove_instruction
from qspice_mcp.services.schematic.rename_component_reference import (
    rename_component_reference,
)
from qspice_mcp.services.schematic.save_schematic_as import save_schematic_as
from qspice_mcp.services.schematic.set_component_parameters import set_component_parameters
from qspice_mcp.services.schematic.set_component_value import set_component_value
from qspice_mcp.services.schematic.set_element_model import set_element_model
from qspice_mcp.services.schematic.set_parameter import set_parameter

_schematic_edits = importlib.import_module("qspice_mcp.services._internals.schematic_edits")
_add_component_service = importlib.import_module("qspice_mcp.services.schematic.add_component")
_add_dll_block_service = importlib.import_module("qspice_mcp.services.schematic.add_dll_block")
_add_instruction_service = importlib.import_module("qspice_mcp.services.schematic.add_instruction")
_add_net_label_service = importlib.import_module("qspice_mcp.services.schematic.add_net_label")
_add_wire_service = importlib.import_module("qspice_mcp.services.schematic.add_wire")
_create_schematic_service = importlib.import_module(
    "qspice_mcp.services.schematic.create_schematic"
)
_create_starter_schematic_service = importlib.import_module(
    "qspice_mcp.services.schematic.create_starter_schematic"
)
_remove_instruction_service = importlib.import_module(
    "qspice_mcp.services.schematic.remove_instruction"
)


class FakeEditor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def save_as(self, destination: str | Path) -> None:
        destination_path = Path(destination)
        destination_path.write_text("edited schematic\n", encoding="utf-8")
        self.calls.append(("save_as", destination_path.resolve(strict=False)))

    def set_component_value(self, reference: str, value: object) -> None:
        self.calls.append(("set_component_value", (reference, value)))

    def set_component_parameters(self, element: str, **kwargs: object) -> None:
        self.calls.append(("set_component_parameters", (element, kwargs)))

    def set_element_model(self, device: str, model: str) -> None:
        self.calls.append(("set_element_model", (device, model)))

    def set_parameter(self, name: str, value: object) -> None:
        self.calls.append(("set_parameter", (name, value)))

    def remove_component(self, reference: str) -> None:
        self.calls.append(("remove_component", reference))

    def add_instruction(self, instruction: str) -> None:
        self.calls.append(("add_instruction", instruction))

    def remove_instruction(self, instruction: str) -> bool:
        self.calls.append(("remove_instruction", instruction))
        return True

    def remove_Xinstruction(self, instruction: str) -> bool:  # noqa: N802
        self.calls.append(("remove_Xinstruction", instruction))
        return True


def _patch_editor(monkeypatch: pytest.MonkeyPatch, editor: FakeEditor, schematic: Path) -> None:
    monkeypatch.setattr(
        _schematic_edits,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            editor,
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )


def test_set_component_value_persists_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited" / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = set_component_value(
        schematic, workspace_root=tmp_path, reference="R1", value="3.3k", output_path=output
    )

    assert result.reference == "R1"
    assert result.output_path == output.resolve(strict=False)
    assert output.is_file()
    assert editor.calls[0] == ("set_component_value", ("R1", "3.3k"))


def test_set_component_parameters_persists_named_updates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = set_component_parameters(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        parameters={"tol": "1%", "temp": 25},
        output_path=output,
    )

    assert result.parameter_names == ("tol", "temp")
    assert editor.calls[0] == ("set_component_parameters", ("R1", {"tol": "1%", "temp": 25}))


def test_set_element_model_persists_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = set_element_model(
        schematic, workspace_root=tmp_path, reference="D1", model="1N4148", output_path=output
    )

    assert result.model == "1N4148"
    assert editor.calls[0] == ("set_element_model", ("D1", "1N4148"))


def test_set_parameter_persists_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = set_parameter(
        schematic, workspace_root=tmp_path, name="TEMP", value=80, output_path=output
    )

    assert result.name == "TEMP"
    assert result.value == "80"
    assert editor.calls[0] == ("set_parameter", ("TEMP", 80))


def test_add_instruction_persists_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = add_instruction(
        schematic, workspace_root=tmp_path, instruction=".tran 5m", output_path=output
    )

    assert result.instruction == ".tran 5m"
    assert editor.calls[0] == ("add_instruction", ".tran 5m")


def test_add_instruction_falls_back_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "blank.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_bytes(blank_schematic_bytes())

    def fail_edit(*args: object, **kwargs: object) -> tuple[Path, Path]:
        del args, kwargs
        raise BackendUnavailableError("no editor backend")

    monkeypatch.setattr(_add_instruction_service, "edit_schematic", fail_edit)

    result = add_instruction(
        schematic,
        workspace_root=tmp_path,
        instruction=".tran 5m",
        output_path=output,
    )
    summary = inspect_schematic(output, workspace_root=tmp_path)

    assert result.output_path == output.resolve(strict=False)
    assert summary.analyses[0].raw == ".tran 5m"


def test_remove_instruction_supports_regex(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = remove_instruction(
        schematic,
        workspace_root=tmp_path,
        instruction=r"\\.AC.*",
        output_path=output,
        regex=True,
    )

    assert result.regex is True
    assert editor.calls[0] == ("remove_Xinstruction", r"\\.AC.*")


def test_remove_instruction_falls_back_without_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "starter.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_bytes(
        starter_schematic_bytes(
            source_reference="V1",
            source_value="10",
            load_reference="R1",
            load_value="1k",
            input_net_name="VIN",
            analysis_instruction=".tran 1m",
        )
    )

    def fail_edit(*args: object, **kwargs: object) -> tuple[Path, Path]:
        del args, kwargs
        raise BackendUnavailableError("no editor backend")

    monkeypatch.setattr(_remove_instruction_service, "edit_schematic", fail_edit)

    result = remove_instruction(
        schematic,
        workspace_root=tmp_path,
        instruction=r"\.tran.*",
        output_path=output,
        regex=True,
    )
    summary = inspect_schematic(output, workspace_root=tmp_path)

    assert result.output_path == output.resolve(strict=False)
    assert result.regex is True
    assert summary.analyses == ()


def test_remove_instruction_raises_when_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    editor.remove_instruction = lambda instruction: False
    _patch_editor(monkeypatch, editor, schematic)

    with pytest.raises(ValueError, match="Instruction was not found"):
        remove_instruction(schematic, workspace_root=tmp_path, instruction=".tran 5m")


def test_save_schematic_as_writes_requested_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "copies" / "demo-copy.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = save_schematic_as(schematic, workspace_root=tmp_path, output_path=output)

    assert result.output_path == output.resolve(strict=False)
    assert output.is_file()
    assert editor.calls[0] == ("save_as", output.resolve(strict=False))


def test_create_schematic_delegates_to_blank_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "blank.qsch"

    monkeypatch.setattr(
        _create_schematic_service,
        "create_blank_schematic_file",
        lambda output_path, *, workspace_root, overwrite=False: (
            Path(output_path).resolve(strict=False),
            overwrite,
        ),
    )

    result = create_schematic(output, workspace_root=tmp_path)

    assert result.output_path == output.resolve(strict=False)
    assert result.overwritten is False


def test_add_component_applies_simple_component_edit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_simple_component(
        editor: object,
        *,
        component_kind: str,
        reference: str | None,
        value: str | int | float | complex | None,
        position: tuple[int, int],
        rotation_degrees: int = 0,
        net_name: str | None = None,
    ) -> str:
        calls.append(
            (
                "add_simple_component",
                (
                    editor,
                    component_kind,
                    reference,
                    value,
                    position,
                    rotation_degrees,
                    net_name,
                ),
            )
        )
        return component_kind

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(_add_component_service, "add_simple_component", fake_add_simple_component)
    monkeypatch.setattr(_add_component_service, "edit_schematic", fake_edit_schematic)

    result = add_component(
        schematic,
        workspace_root=tmp_path,
        component_kind="resistor",
        reference="R1",
        value="10k",
        position_x=160,
        position_y=240,
        rotation_degrees=90,
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.component_kind == "resistor"
    assert result.reference == "R1"
    assert result.value == "10k"
    assert result.net_name is None
    assert calls[0][0] == "add_simple_component"
    assert calls[0][1][1:] == ("resistor", "R1", "10k", (160, 240), 90, None)


def test_add_component_supports_ground_without_reference_or_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_simple_component(
        editor: object,
        *,
        component_kind: str,
        reference: str | None,
        value: str | int | float | complex | None,
        position: tuple[int, int],
        rotation_degrees: int = 0,
        net_name: str | None = None,
    ) -> str:
        calls.append(
            (
                "add_simple_component",
                (
                    editor,
                    component_kind,
                    reference,
                    value,
                    position,
                    rotation_degrees,
                    net_name,
                ),
            )
        )
        return "ground"

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(_add_component_service, "add_simple_component", fake_add_simple_component)
    monkeypatch.setattr(_add_component_service, "edit_schematic", fake_edit_schematic)

    result = add_component(
        schematic,
        workspace_root=tmp_path,
        component_kind="ground",
        position_x=0,
        position_y=400,
    )

    assert result.component_kind == "ground"
    assert result.reference is None
    assert result.value is None
    assert result.net_name == "GND"
    assert calls[0][1][1:] == ("ground", None, None, (0, 400), 0, None)


def test_add_dll_block_applies_custom_device_edit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_dll_block(
        editor: object,
        *,
        reference: str,
        device_name: str,
        input_pin_names: tuple[str, ...] | list[str],
        output_pin_names: tuple[str, ...] | list[str],
        position: tuple[int, int],
        rotation_degrees: int = 0,
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        calls.append(
            (
                "add_dll_block",
                (
                    editor,
                    reference,
                    device_name,
                    tuple(input_pin_names),
                    tuple(output_pin_names),
                    position,
                    rotation_degrees,
                ),
            )
        )
        return tuple(input_pin_names), tuple(output_pin_names)

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(_add_dll_block_service, "add_dll_block_backend", fake_add_dll_block)
    monkeypatch.setattr(_add_dll_block_service, "edit_schematic", fake_edit_schematic)

    result = add_dll_block(
        schematic,
        workspace_root=tmp_path,
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=["in0", "clk"],
        output_pin_names=["pwm"],
        position_x=300,
        position_y=100,
        rotation_degrees=45,
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.reference == "X1"
    assert result.device_name == "Buck_controller"
    assert result.input_pin_names == ("in0", "clk")
    assert result.output_pin_names == ("pwm",)
    assert calls[0][0] == "add_dll_block"
    assert calls[0][1][1:] == (
        "X1",
        "Buck_controller",
        ("in0", "clk"),
        ("pwm",),
        (300, 100),
        45,
    )


def test_add_wire_applies_wire_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_wire(
        editor: object,
        *,
        start: tuple[int, int],
        end: tuple[int, int],
        net_name: str,
    ) -> str:
        calls.append(("add_wire", (editor, start, end, net_name)))
        return net_name

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(
        _add_wire_service,
        "resolve_wire_points",
        lambda editor, **kwargs: ((0, 0), (400, 0)),
    )
    monkeypatch.setattr(_add_wire_service, "add_wire_segment", fake_add_wire)
    monkeypatch.setattr(_add_wire_service, "edit_schematic", fake_edit_schematic)

    result = add_wire(
        schematic,
        workspace_root=tmp_path,
        start_x=0,
        start_y=0,
        end_x=400,
        end_y=0,
        net_name="VIN",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.net_name == "VIN"
    assert calls[0][1][1:] == ((0, 0), (400, 0), "VIN")
    assert result.start_reference is None
    assert result.end_reference is None


def test_add_wire_supports_pin_selected_endpoints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_wire(
        editor: object,
        *,
        start: tuple[int, int],
        end: tuple[int, int],
        net_name: str,
    ) -> str:
        calls.append(("add_wire", (editor, start, end, net_name)))
        return net_name

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(
        _add_wire_service,
        "resolve_wire_points",
        lambda editor, **kwargs: ((400, 600), (800, 600)),
    )
    monkeypatch.setattr(_add_wire_service, "add_wire_segment", fake_add_wire)
    monkeypatch.setattr(_add_wire_service, "edit_schematic", fake_edit_schematic)

    result = add_wire(
        schematic,
        workspace_root=tmp_path,
        start_reference="V1",
        start_pin="+",
        end_reference="R1",
        end_pin="1",
        net_name="VOUT",
    )

    assert result.start_x == 400
    assert result.end_x == 800
    assert result.start_reference == "V1"
    assert result.start_pin == "+"
    assert result.end_reference == "R1"
    assert result.end_pin == "1"
    assert calls[0][1][1:] == ((400, 600), (800, 600), "VOUT")


def test_add_net_label_applies_label_edit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    calls: list[tuple[str, object]] = []

    def fake_add_net_label(
        editor: object,
        *,
        position: tuple[int, int],
        net_name: str,
    ) -> str:
        calls.append(("add_net_label", (editor, position, net_name)))
        return net_name

    def fake_edit_schematic(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        apply_edit: object | None = None,
    ) -> tuple[Path, Path]:
        del workspace_root
        fake_editor = object()
        assert callable(apply_edit)
        apply_edit(fake_editor)
        saved_path = Path(output_path or schematic_path).resolve(strict=False)
        saved_path.write_text("edited schematic\n", encoding="utf-8")
        return Path(schematic_path).resolve(strict=False), saved_path

    monkeypatch.setattr(_add_net_label_service, "add_net_label_tag", fake_add_net_label)
    monkeypatch.setattr(_add_net_label_service, "edit_schematic", fake_edit_schematic)

    result = add_net_label(
        schematic,
        workspace_root=tmp_path,
        position_x=0,
        position_y=0,
        net_name="VIN",
        output_path=output,
    )

    assert result.output_path == output.resolve(strict=False)
    assert result.net_name == "VIN"
    assert calls[0][1][1:] == ((0, 0), "VIN")


def test_create_starter_schematic_orchestrates_blank_template_creation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "starter.qsch"
    editor = FakeEditor()
    calls: list[tuple[str, object]] = []

    def fake_factory(path: str, create_blank: bool = False) -> FakeEditor:
        calls.append(("factory", (Path(path).resolve(strict=False), create_blank)))
        return editor

    def fake_add_simple_component(
        editor_obj: object,
        *,
        component_kind: str,
        reference: str | None,
        value: str | int | float | complex | None,
        position: tuple[int, int],
        rotation_degrees: int = 0,
        net_name: str | None = None,
    ) -> str:
        calls.append(
            (
                "add_simple_component",
                (
                    editor_obj,
                    component_kind,
                    reference,
                    value,
                    position,
                    rotation_degrees,
                    net_name,
                ),
            )
        )
        return component_kind

    def fake_add_wire(editor_obj: object, **kwargs: object) -> str:
        calls.append(("add_wire", (editor_obj, kwargs)))
        return str(kwargs["net_name"])

    def fake_add_net_label(editor_obj: object, **kwargs: object) -> str:
        calls.append(("add_net_label", (editor_obj, kwargs)))
        return str(kwargs["net_name"])

    def fake_resolve_component_pin_position(
        editor_obj: object,
        *,
        reference: str,
        pin_name: str,
    ) -> tuple[int, int]:
        del editor_obj
        mapping = {
            ("V1", "+"): (400, 600),
            ("V1", "-"): (400, 200),
            ("R1", "2"): (800, 200),
        }
        return mapping[(reference, pin_name)]

    def fake_save_editor_as(
        editor_obj: object,
        *,
        workspace_root: Path,
        output_path: str | Path | None,
        default: Path,
    ) -> Path:
        del editor_obj, workspace_root, default
        resolved = Path(output_path).resolve(strict=False)
        resolved.write_text("starter schematic\n", encoding="utf-8")
        calls.append(("save_editor_as", resolved))
        return resolved

    monkeypatch.setattr(
        _create_starter_schematic_service,
        "load_qsch_editor_factory",
        lambda: (fake_factory, "fake"),
    )
    monkeypatch.setattr(
        _create_starter_schematic_service,
        "bootstrap_blank_schematic",
        lambda editor_obj: calls.append(("bootstrap_blank_schematic", editor_obj)),
    )
    monkeypatch.setattr(
        _create_starter_schematic_service,
        "add_simple_component",
        fake_add_simple_component,
    )
    monkeypatch.setattr(_create_starter_schematic_service, "add_wire", fake_add_wire)
    monkeypatch.setattr(_create_starter_schematic_service, "add_net_label", fake_add_net_label)
    monkeypatch.setattr(
        _create_starter_schematic_service,
        "resolve_component_pin_position",
        fake_resolve_component_pin_position,
    )
    monkeypatch.setattr(_create_starter_schematic_service, "save_editor_as", fake_save_editor_as)

    result = create_starter_schematic(output, workspace_root=tmp_path)

    assert result.output_path == output.resolve(strict=False)
    assert result.overwritten is False
    assert result.source_reference == "V1"
    assert result.load_reference == "R1"
    assert result.input_net_name == "VIN"
    assert result.analysis_instruction == ".op"
    assert ("bootstrap_blank_schematic", editor) in calls
    assert (
        "add_simple_component",
        (editor, "voltage_source", "V1", "10", (400, 400), 0, None),
    ) in calls
    assert (
        "add_simple_component",
        (editor, "resistor", "R1", "1k", (800, 400), 0, None),
    ) in calls
    assert (
        "add_simple_component",
        (editor, "ground", None, None, (800, 200), 0, None),
    ) in calls
    assert (
        "add_simple_component",
        (editor, "ground", None, None, (400, 200), 0, None),
    ) in calls
    assert ("add_instruction", ".op") in editor.calls


# ---------------------------------------------------------------------------
# rename_component_reference
# ---------------------------------------------------------------------------

_rename_service = importlib.import_module(
    "qspice_mcp.services.schematic.rename_component_reference"
)


class FakeRenameEditor(FakeEditor):
    def __init__(self) -> None:
        super().__init__()
        self.components: dict[str, object] = {}
        self.updated = False

    def get_components(self, prefixes: str = "*") -> list[str]:
        return list(self.components.keys())

    def get_component(self, reference: str) -> object:
        return self.components[reference]


class FakeRenameComponent:
    reference: str

    def __init__(self, reference: str) -> None:
        self.reference = reference
        self.attributes: dict[str, object] = {}


class FakeSymbolTag:
    def __init__(self) -> None:
        self.texts = [_FakeTextTag("R1"), _FakeTextTag("1k")]

    def get_items(self, label: str) -> list[object]:
        if label == "text":
            return self.texts
        return []


class _FakeTextTag:
    def __init__(self, text: str = "R1") -> None:
        self._attrs: dict[int, object] = {}
        self._text = text

    def set_attr(self, index: int, value: object) -> None:
        self._attrs[index] = value

    def get_attr(self, index: int) -> object:
        return self._attrs.get(index, self._text)


class FakeQschModule:
    QSCH_SYMBOL_TEXT_REFDES = 0
    QSCH_SYMBOL_TEXT_VALUE = 1
    QSCH_TEXT_STR_ATTR = 8


def _make_rename_editor(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[FakeRenameEditor, Path, Path]:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    editor = FakeRenameEditor()
    _patch_editor(monkeypatch, editor, schematic)

    monkeypatch.setattr(
        _rename_service,
        "_component_symbol_tag",
        lambda editor_obj, *, reference: (object(), FakeSymbolTag()),
    )
    monkeypatch.setattr(
        _rename_service,
        "_load_qsch_support_modules",
        lambda: (FakeQschModule(), object()),
    )

    return editor, schematic, output


def test_rename_component_reference_changes_symbol_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    editor, schematic, output = _make_rename_editor(monkeypatch, tmp_path)

    comp = FakeRenameComponent("R1")
    editor.components["R1"] = comp

    result = rename_component_reference(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        new_reference="R2",
        output_path=output,
    )

    assert result.reference == "R1"
    assert result.new_reference == "R2"
    assert result.schematic_path == schematic.resolve(strict=False)
    assert result.output_path == output.resolve(strict=False)
    assert editor.updated is True
    assert "R2" in editor.components
    assert "R1" not in editor.components


def test_rename_component_reference_rejects_duplicate_new_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    editor, schematic, _ = _make_rename_editor(monkeypatch, tmp_path)
    editor.components["R1"] = FakeRenameComponent("R1")
    editor.components["R2"] = FakeRenameComponent("R2")

    with pytest.raises(ValueError, match="already exists"):
        rename_component_reference(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            new_reference="R2",
        )


def test_rename_component_reference_rejects_empty_new_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    editor, schematic, _ = _make_rename_editor(monkeypatch, tmp_path)  # noqa: RUF059

    with pytest.raises(ValueError, match="must not be empty"):
        rename_component_reference(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            new_reference="  ",
        )


def test_rename_component_reference_clears_old_dict_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    editor, schematic, output = _make_rename_editor(monkeypatch, tmp_path)
    editor.components["R1"] = FakeRenameComponent("R1")

    rename_component_reference(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        new_reference="RLOAD",
        output_path=output,
    )

    assert "R1" not in editor.components
    assert "RLOAD" in editor.components
    assert editor.components["RLOAD"].reference == "RLOAD"


# ---------------------------------------------------------------------------
# describe_edit_capability
# ---------------------------------------------------------------------------

_describe_capability_service = importlib.import_module(
    "qspice_mcp.services.schematic.describe_edit_capability"
)


def _patch_read_component(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Patch read_component so describe_edit_capability returns a known component."""
    from qspice_mcp.services.schematic.read_component import ComponentRead  # noqa: PLC0415

    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")

    fake_component = ComponentRead(
        schematic_path=schematic.resolve(strict=False),
        reference="R1",
        kind="R",
        value="1k",
        description="Resistor(USA Style Symbol)",
        nodes=("N01", "0"),
        parameters={},
        raw_parameter_lines=(),
        position_x=400,
        position_y=400,
        rotation_degrees=0,
        has_subcircuit=False,
    )

    monkeypatch.setattr(
        _describe_capability_service,
        "read_component",
        lambda schematic_path, *, workspace_root, reference: fake_component,
    )
    return schematic


def _patch_backend_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _describe_capability_service,
        "open_schematic_editor",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            BackendUnavailableError("no backend"),
        ),
    )


def test_describe_edit_capability_rename_reference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="rename_reference",
    )

    assert result.supported is True
    assert result.suggested_tool == "rename_component_reference"
    assert result.reference == "R1"
    assert result.component_kind == "R"


def test_describe_edit_capability_change_value(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="change_value",
    )

    assert result.supported is True
    assert result.suggested_tool == "set_component_value"
    assert result.suggested_parameters.get("value") == "1k"


def test_describe_edit_capability_change_value_supports_voltage_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from qspice_mcp.services.schematic.read_component import ComponentRead  # noqa: PLC0415

    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    fake_component = ComponentRead(
        schematic_path=schematic.resolve(strict=False),
        reference="V1",
        kind="V",
        value="10",
        description="Independent Voltage Source",
        nodes=("N01", "0"),
        parameters={"Value": "10"},
        raw_parameter_lines=(),
        position_x=400,
        position_y=400,
        rotation_degrees=0,
        has_subcircuit=False,
    )
    monkeypatch.setattr(
        _describe_capability_service,
        "read_component",
        lambda schematic_path, *, workspace_root, reference: fake_component,
    )
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="V1",
        intent="change_value",
    )

    assert result.supported is True
    assert result.suggested_tool == "set_component_value"
    assert result.suggested_parameters.get("value") == "10"


def test_describe_edit_capability_move_component_targets_unified_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="move_component",
    )

    assert result.supported is True
    assert result.suggested_tool == "set_component_position"
    assert result.suggested_parameters.get("position_x") == 400
    assert result.suggested_parameters.get("position_y") == 400


def test_describe_edit_capability_rotate_component_targets_unified_tool(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="rotate_component",
    )

    assert result.supported is True
    assert result.suggested_tool == "set_component_position"
    assert result.suggested_parameters.get("rotation_degrees") == 0


def test_describe_edit_capability_delete_component_supported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="delete_component",
    )

    assert result.supported is True
    assert result.suggested_tool == "remove_component"
    assert result.suggested_parameters.get("reference") == "R1"


def test_describe_edit_capability_symbol_intent_no_backend(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    result = describe_edit_capability(
        schematic,
        workspace_root=tmp_path,
        reference="R1",
        intent="edit_symbol_text",
    )

    assert result.supported is False
    assert result.unsupported_reason is not None
    assert "backend" in result.unsupported_reason.lower()


def test_describe_edit_capability_rejects_invalid_intent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = _patch_read_component(monkeypatch, tmp_path)
    _patch_backend_unavailable(monkeypatch)

    with pytest.raises(ValueError, match="Unsupported edit intent"):
        describe_edit_capability(
            schematic,
            workspace_root=tmp_path,
            reference="R1",
            intent="fly_to_moon",
        )


# ---------------------------------------------------------------------------
# describe_schematic_edit_support
# ---------------------------------------------------------------------------


def test_describe_schematic_edit_support_returns_full_catalog() -> None:
    result = describe_schematic_edit_support()

    assert len(result.supported_intents) >= 8
    intents = {e.intent for e in result.supported_intents}
    assert "rename_reference" in intents
    assert "change_value" in intents
    assert "delete_component" in intents
    delete_entry = next(e for e in result.supported_intents if e.intent == "delete_component")
    assert delete_entry.supported is True
    assert delete_entry.tool == "remove_component"


# ---------------------------------------------------------------------------
# remove_component
# ---------------------------------------------------------------------------


def test_remove_component_delegates_to_editor(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    schematic = tmp_path / "demo.qsch"
    output = tmp_path / "edited.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    editor = FakeEditor()
    _patch_editor(monkeypatch, editor, schematic)

    result = remove_component(
        schematic, workspace_root=tmp_path, reference="R1", output_path=output
    )

    assert result.reference == "R1"
    assert result.output_path == output.resolve(strict=False)
    assert ("remove_component", "R1") in editor.calls
