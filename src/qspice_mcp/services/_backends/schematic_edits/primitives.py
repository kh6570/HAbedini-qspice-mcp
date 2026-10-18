# In the name of God, the Most Gracious, the Most Merciful
"""Schematic edit helpers: primitives."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, cast

from ..schematic_editor_backend import (
    _BEHAVIORAL_REFERENCE_PREFIX,
    _CAPACITOR_REFERENCE_PREFIX,
    _DIODE_REFERENCE_PREFIX,
    _GROUND_NET_NAME,
    _INDUCTOR_REFERENCE_PREFIX,
    _MOSFET_REFERENCE_PREFIX,
    _RESISTOR_REFERENCE_PREFIX,
    _VOLTAGE_SOURCE_REFERENCE_PREFIX,
    SimpleComponentKind,
    _load_qsch_support_modules,
    _normalize_component_kind,
    _QschEditorProtocol,
    _SchematicComponentProtocol,
    component_rotation_degrees_to_index,
    component_rotation_index_to_degrees,
)
from .dll_block import _build_dll_block_component, _normalize_dll_pin_names
from .structure import _append_schematic_tag, bootstrap_blank_schematic
from .wiring import add_net_label

if TYPE_CHECKING:
    from collections.abc import Callable


def _build_two_pin_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    reference_prefix: str,
    symbol_name: str,
    type_name: str,
    description: str,
    default_value: str,
    drawing_defs: tuple[tuple[object, ...], ...],
    pin_defs: tuple[tuple[object, ...], ...],
    port_names: tuple[str, str],
    refdes_text_position: str = "(100,150)",
    value_text_position: str = "(100,-150)",
    library_file: str | None = None,
) -> _SchematicComponentProtocol:
    """Create one two-pin schematic component object ready for insertion."""

    if not reference.upper().startswith(reference_prefix):
        raise ValueError(f"{symbol_name} references must start with '{reference_prefix}'.")

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    tag_class = qsch_module.QschTag
    component = base_schematic_module.SchematicComponent(editor, reference)
    component_tag = tag_class("component", "(0,0)", 0, 0)
    symbol_tag = tag_class("symbol", symbol_name)
    symbol_tag.items.append(tag_class("type:", type_name))
    symbol_tag.items.append(tag_class("description:", description))
    if library_file is not None:
        symbol_tag.items.append(tag_class("library file:", library_file))
    symbol_tag.items.append(tag_class("shorted pins:", "false"))
    for item_def in drawing_defs:
        symbol_tag.items.append(tag_class(*item_def))
    symbol_tag.items.append(
        tag_class("text", refdes_text_position, 1, 7, 0, "0x1000000", -1, -1, '""')
    )
    symbol_tag.items.append(
        tag_class("text", value_text_position, 1, 7, 0, "0x1000000", -1, -1, '""')
    )
    for item_def in pin_defs:
        symbol_tag.items.append(tag_class(*item_def))
    component_tag.items.append(symbol_tag)

    texts = symbol_tag.get_items("text")
    texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(qsch_module.QSCH_TEXT_STR_ATTR, reference)
    texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].set_attr(
        qsch_module.QSCH_TEXT_STR_ATTR, default_value
    )

    component.reference = reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    component.attributes["type"] = type_name
    component.attributes["description"] = description
    if library_file is not None:
        component.attributes["library file"] = library_file
    component.attributes["value"] = default_value
    component.attributes["tag"] = component_tag
    component.attributes["enabled"] = True
    component.ports = list(port_names)
    return cast("_SchematicComponentProtocol", component)


def _build_resistor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one resistor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_RESISTOR_REFERENCE_PREFIX,
        symbol_name="R",
        type_name="R",
        description="Resistor(USA Style Symbol)",
        default_value="1",
        drawing_defs=(
            ("line", "(0,200)", "(0,180)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-180)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            (
                "zigzag",
                "(-80,180)",
                "(80,-180)",
                0,
                0,
                0,
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"1"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"2"'),
        ),
        port_names=("1", "2"),
    )


def _build_capacitor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one capacitor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_CAPACITOR_REFERENCE_PREFIX,
        symbol_name="C",
        type_name="C",
        description="Capacitor",
        default_value="1u",
        drawing_defs=(
            ("line", "(0,200)", "(0,40)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-40)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            (
                "rect",
                "(-130,-40)",
                "(130,-30)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-130,30)",
                "(130,40)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
    )


def _build_diode_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one diode component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_DIODE_REFERENCE_PREFIX,
        symbol_name="D",
        type_name="D",
        description="Silicon Diode",
        default_value="D",
        drawing_defs=(
            ("line", "(100,80)", "(-100,80)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,80)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-200)", "(0,-70)", 0, 0, "0x1000000", -1, -1),
            (
                "triangle",
                "(0,80)",
                "(100,-70)",
                "(-100,-70)",
                0,
                0,
                "0x1000000",
                "0x2000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"A"'),
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"K"'),
        ),
        port_names=("A", "K"),
        refdes_text_position="(100,200)",
        value_text_position="(100,-200)",
        library_file="Diode.txt",
    )


def _build_voltage_source_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one independent voltage source component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_VOLTAGE_SOURCE_REFERENCE_PREFIX,
        symbol_name="V",
        type_name="V",
        description="Independent Voltage Source",
        default_value="1",
        drawing_defs=(
            ("line", "(0,-130)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,130)", 0, 0, "0x1000000", -1, -1),
            (
                "rect",
                "(-25,77)",
                "(25,73)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-2,50)",
                "(2,100)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "rect",
                "(-25,-73)",
                "(25,-77)",
                0,
                0,
                0,
                "0x1000000",
                "0x3000000",
                -1,
                0,
                -1,
            ),
            (
                "ellipse",
                "(-130,130)",
                "(130,-130)",
                0,
                0,
                0,
                "0x1000000",
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
        value_text_position="(0,380)",
    )


def _build_inductor_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one inductor component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_INDUCTOR_REFERENCE_PREFIX,
        symbol_name="L",
        type_name="L",
        description="Inductor",
        default_value="1u",
        drawing_defs=(
            ("line", "(0,200)", "(0,180)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,-200)", "(0,-180)", 0, 0, "0x1000000", -1, -1),
            ("coil", "(-80,180)", "(80,-180)", 0, 0, 0, "0x1000000", -1, -1),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"1"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"2"'),
        ),
        port_names=("1", "2"),
        refdes_text_position="(80,0)",
        value_text_position="(-80,0)",
    )


def _build_behavioral_source_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Create one behavioral voltage source component object ready for insertion."""

    return _build_two_pin_component(
        editor,
        reference=reference,
        reference_prefix=_BEHAVIORAL_REFERENCE_PREFIX,
        symbol_name="B",
        type_name="B",
        description="Behavioral Voltage Source",
        default_value="V=0",
        drawing_defs=(
            ("line", "(0,-130)", "(0,-200)", 0, 0, "0x1000000", -1, -1),
            ("line", "(0,200)", "(0,130)", 0, 0, "0x1000000", -1, -1),
            ("rect", "(-25,77)", "(25,73)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            ("rect", "(-2,50)", "(2,100)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            ("rect", "(-25,-73)", "(25,-77)", 0, 0, 0, "0x1000000", "0x3000000", -1, 0, -1),
            (
                "ellipse",
                "(-130,130)",
                "(130,-130)",
                0,
                0,
                0,
                "0x1000000",
                "0x1000000",
                -1,
                -1,
            ),
        ),
        pin_defs=(
            ("pin", "(0,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"+"'),
            ("pin", "(0,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"-"'),
        ),
        port_names=("+", "-"),
        refdes_text_position="(130,0)",
        value_text_position="(-130,0)",
    )


def _build_mosfet_component(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    polarity: Literal["nmos", "pmos"],
) -> _SchematicComponentProtocol:
    """Create one library-backed MOSFET component object ready for insertion."""

    if not reference.upper().startswith(_MOSFET_REFERENCE_PREFIX):
        raise ValueError(f"MOSFET references must start with '{_MOSFET_REFERENCE_PREFIX}'.")

    if polarity == "nmos":
        symbol_name = "NMOS"
        type_name = "MN"
        description = "N-Channel MOSFET Transistor"
        library_file = "NMOS.txt"
        default_value = "NMOS"
        channel_triangle = (
            "triangle",
            "(70,-150)",
            "(-25,-125)",
            "(-25,-175)",
            0,
            0,
            "0x1000000",
            "0x3000000",
            -1,
            -1,
        )
    else:
        symbol_name = "PMOS"
        type_name = "MP"
        description = "P-Channel MOSFET Transistor"
        library_file = "PMOS.txt"
        default_value = "PMOS"
        channel_triangle = (
            "triangle",
            "(-25,-125)",
            "(70,-150)",
            "(70,-175)",
            0,
            0,
            "0x1000000",
            "0x3000000",
            -1,
            -1,
        )

    qsch_module, base_schematic_module = _load_qsch_support_modules()
    tag_class = qsch_module.QschTag
    component = base_schematic_module.SchematicComponent(editor, reference)
    component_tag = tag_class("component", "(0,0)", 0, 0)
    symbol_tag = tag_class("symbol", symbol_name)
    symbol_tag.items.append(tag_class("type:", type_name))
    symbol_tag.items.append(tag_class("description:", description))
    symbol_tag.items.append(tag_class("library file:", library_file))
    symbol_tag.items.append(tag_class("shorted pins:", "false"))
    for item_def in (
        ("line", "(100,200)", "(100,150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,-150)", "(100,-200)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-100,150)", "(-100,-150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-100,0)", "(-200,0)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,-150)", "(-50,-150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(100,150)", "(-50,150)", 0, 0, "0x1000000", -1, -1),
        ("line", "(-50,150)", "(-50,-150)", 0, 0, "0x1000000", -1, -1),
        channel_triangle,
    ):
        symbol_tag.items.append(tag_class(*item_def))
    symbol_tag.items.append(tag_class("text", "(100,-200)", 1, 102, 0, "0x1000000", -1, -1, '""'))
    symbol_tag.items.append(tag_class("text", "(-200,1200)", 1, 103, 0, "0x1000000", -1, -1, '""'))
    for pin_def in (
        ("pin", "(100,200)", "(0,0)", 1, 0, 0, "0x0", -1, '"D"'),
        ("pin", "(-200,0)", "(0,0)", 1, 0, 0, "0x0", -1, '"G"'),
        ("pin", "(100,-200)", "(0,0)", 1, 0, 0, "0x0", -1, '"S"'),
    ):
        symbol_tag.items.append(tag_class(*pin_def))
    component_tag.items.append(symbol_tag)

    texts = symbol_tag.get_items("text")
    texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(qsch_module.QSCH_TEXT_STR_ATTR, reference)
    texts[qsch_module.QSCH_SYMBOL_TEXT_VALUE].set_attr(
        qsch_module.QSCH_TEXT_STR_ATTR, default_value
    )

    component.reference = reference
    component.position = base_schematic_module.Point(0, 0)
    component.rotation = 0
    component.attributes["type"] = type_name
    component.attributes["description"] = description
    component.attributes["library file"] = library_file
    component.attributes["value"] = default_value
    component.attributes["tag"] = component_tag
    component.attributes["enabled"] = True
    component.ports = ["D", "G", "S"]
    return cast("_SchematicComponentProtocol", component)


def _build_simple_component(
    editor: _QschEditorProtocol,
    normalized_kind: str,
    *,
    reference: str,
) -> _SchematicComponentProtocol:
    """Construct the component object for one normalized simple-component kind."""

    builders: dict[str, Callable[[], _SchematicComponentProtocol]] = {
        "resistor": lambda: _build_resistor_component(editor, reference=reference),
        "capacitor": lambda: _build_capacitor_component(editor, reference=reference),
        "diode": lambda: _build_diode_component(editor, reference=reference),
        "voltage_source": lambda: _build_voltage_source_component(editor, reference=reference),
        "inductor": lambda: _build_inductor_component(editor, reference=reference),
        "behavioral": lambda: _build_behavioral_source_component(editor, reference=reference),
        "nmos": lambda: _build_mosfet_component(editor, reference=reference, polarity="nmos"),
        "pmos": lambda: _build_mosfet_component(editor, reference=reference, polarity="pmos"),
    }
    builder = builders.get(normalized_kind)
    if builder is None:
        raise AssertionError(f"Unhandled component kind: {normalized_kind}")
    return builder()


def add_simple_component(
    editor: _QschEditorProtocol,
    *,
    component_kind: str,
    reference: str | None,
    value: str | int | float | complex | None,
    position: tuple[int, int],
    rotation_degrees: int = 0,
    net_name: str | None = None,
) -> SimpleComponentKind:
    """Add one supported simple component to the current editor."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    normalized_kind = _normalize_component_kind(component_kind)
    bootstrap_blank_schematic(editor)

    if normalized_kind == "ground":
        add_net_label(
            editor,
            net_name=net_name or _GROUND_NET_NAME,
            position=position,
        )
        return normalized_kind

    if reference is None or not reference.strip():
        raise ValueError(f"{normalized_kind} components require a non-empty reference.")
    if value is None:
        raise ValueError(f"{normalized_kind} components require a value.")

    existing_references = {str(item) for item in editor.get_components(prefixes="*")}
    if reference in existing_references:
        raise ValueError(f"Component reference already exists in schematic: {reference}")

    component = _build_simple_component(editor, normalized_kind, reference=reference)

    editor.add_component(component)
    _append_schematic_tag(editor, component.attributes["tag"])
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(reference, position, rotation_index)
    editor.set_component_value(reference, value)
    editor.updated = True
    return normalized_kind


def add_dll_block(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    device_name: str,
    input_pin_names: tuple[str, ...] | list[str],
    output_pin_names: tuple[str, ...] | list[str],
    position: tuple[int, int],
    rotation_degrees: int = 0,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Add one `.DLL` custom-device block to the current editor."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    bootstrap_blank_schematic(editor)

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError(".DLL blocks require a non-empty reference.")

    normalized_input_pin_names = _normalize_dll_pin_names(input_pin_names)
    normalized_output_pin_names = _normalize_dll_pin_names(output_pin_names)

    existing_references = {str(item) for item in editor.get_components(prefixes="*")}
    if normalized_reference in existing_references:
        raise ValueError(f"Component reference already exists in schematic: {normalized_reference}")

    component = _build_dll_block_component(
        editor,
        reference=normalized_reference,
        device_name=device_name,
        input_pin_names=normalized_input_pin_names,
        output_pin_names=normalized_output_pin_names,
    )

    editor.add_component(component)
    _append_schematic_tag(editor, component.attributes["tag"])
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(normalized_reference, position, rotation_index)
    editor.set_component_value(normalized_reference, device_name)
    editor.updated = True
    return normalized_input_pin_names, normalized_output_pin_names


def set_component_rotation(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    rotation_degrees: int,
) -> int:
    """Rotate one placed component without changing its position."""

    if rotation_degrees % 45 != 0:
        raise ValueError("rotation_degrees must be a multiple of 45.")

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")

    position, _rotation = editor.get_component_position(normalized_reference)
    rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    editor.set_component_position(normalized_reference, position, rotation_index)
    editor.updated = True
    return rotation_degrees


def set_component_position(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    position_x: int,
    position_y: int,
    rotation_degrees: int | None = None,
) -> tuple[int, int, int]:
    """Move one placed component and optionally update its rotation."""

    normalized_reference = reference.strip()
    if not normalized_reference:
        raise ValueError("reference must not be empty.")

    _position, rotation_index_raw = editor.get_component_position(normalized_reference)
    if not isinstance(rotation_index_raw, int):
        raise TypeError(f"Unsupported component rotation index: {rotation_index_raw!r}")
    rotation_index = rotation_index_raw
    if rotation_degrees is not None:
        if rotation_degrees % 45 != 0:
            raise ValueError("rotation_degrees must be a multiple of 45.")
        rotation_index = component_rotation_degrees_to_index(rotation_degrees)
    else:
        rotation_degrees = component_rotation_index_to_degrees(rotation_index)

    editor.set_component_position(
        normalized_reference,
        (int(position_x), int(position_y)),
        rotation_index,
    )
    editor.updated = True
    return int(position_x), int(position_y), rotation_degrees
