"""Backend loader and shared normalization helpers for schematic editing."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from qspice_mcp.core.exceptions import BackendUnavailableError, QSpiceError
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file

if TYPE_CHECKING:
    from pathlib import Path

_EDITOR_MODULE_CANDIDATES: tuple[str, ...] = ("qspice_mcp.services._backends._qsch_editor",)
_POINT_COORDINATE_COUNT = 2
_GROUND_NET_NAME = "GND"
_NET_LABEL_KIND = 1
_NET_LABEL_STYLE_DEFAULT = 14
_NET_LABEL_STYLE_GROUND = 13
_NET_LABEL_FLAGS = 0
_ROTATION_STEP_DEGREES = 45
_ROTATION_INDEX_MAX = 7
_MIRROR_ROTATION_OFFSET = 8
_MIRROR_ROTATION_INDEX_MAX = 15
_PIN_POSITION_ROUNDING_DIGITS = -2
_SYMBOL_PIN_TEXT_SIZE = 3
_SYMBOL_PIN_LABEL_ANCHOR = 4
_SYMBOL_PIN_KIND = 5
_SYMBOL_PIN_COLOR = 6
_SYMBOL_PIN_AUX = 7
_RESISTOR_REFERENCE_PREFIX = "R"
_CAPACITOR_REFERENCE_PREFIX = "C"
_DIODE_REFERENCE_PREFIX = "D"
_VOLTAGE_SOURCE_REFERENCE_PREFIX = "V"
_INDUCTOR_REFERENCE_PREFIX = "L"
_BEHAVIORAL_REFERENCE_PREFIX = "B"
_MOSFET_REFERENCE_PREFIX = "M"
_IMAGE_FILE_SUFFIXES = (
    ".bmp",
    ".dib",
    ".gif",
    ".jpg",
    ".jpeg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
)
_SYMBOL_METADATA_TAGS = frozenset(
    {"description:", "library file:", "pin", "shorted pins:", "text", "type:"}
)


@dataclass(frozen=True, slots=True)
class SymbolTextMetadata:
    """Normalized metadata for one symbol text item."""

    index: int
    role: str
    text: str
    position_x: int
    position_y: int
    size: int
    rotation_code: int
    rotation_degrees: int | None
    is_comment: bool
    color_code: str


@dataclass(frozen=True, slots=True)
class SymbolPinMetadata:
    """Normalized metadata for one symbol pin item."""

    index: int
    name: str
    position_x: int
    position_y: int
    label_position_x: int
    label_position_y: int
    text_size: int
    label_anchor_code: int
    pin_kind_code: int
    color_code: str
    aux_code: int
    behavioral_net_override: str | None = None


@dataclass(frozen=True, slots=True)
class SymbolDrawingMetadata:
    """Normalized metadata for one non-text, non-pin symbol drawing item."""

    index: int
    tag_name: str
    arguments: tuple[str, ...]
    coordinate_points: tuple[tuple[int, int], ...]
    image_asset_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComponentSymbolMetadata:
    """Normalized metadata for one component's embedded symbol."""

    symbol_name: str
    type_name: str | None
    description: str | None
    library_file: str | None
    shorted_pins: bool | None
    text_attributes: tuple[SymbolTextMetadata, ...]
    pins: tuple[SymbolPinMetadata, ...]
    drawing_items: tuple[SymbolDrawingMetadata, ...]
    drawing_tags: tuple[str, ...]
    image_asset_tokens: tuple[str, ...]


SimpleComponentKind = Literal[
    "resistor",
    "capacitor",
    "diode",
    "voltage_source",
    "inductor",
    "behavioral",
    "nmos",
    "pmos",
    "ground",
]

_SIMPLE_COMPONENT_KIND_ALIASES: dict[str, SimpleComponentKind] = {
    "b": "behavioral",
    "behavioral": "behavioral",
    "behavioral_source": "behavioral",
    "behavioral-source": "behavioral",
    "behavioral_voltage_source": "behavioral",
    "c": "capacitor",
    "cap": "capacitor",
    "capacitor": "capacitor",
    "d": "diode",
    "diode": "diode",
    "ground": "ground",
    "gnd": "ground",
    "inductor": "inductor",
    "l": "inductor",
    "mn": "nmos",
    "mosfet": "nmos",
    "mp": "pmos",
    "nmos": "nmos",
    "n-channel": "nmos",
    "pmos": "pmos",
    "p-channel": "pmos",
    "r": "resistor",
    "res": "resistor",
    "resistor": "resistor",
    "v": "voltage_source",
    "voltage": "voltage_source",
    "voltage_source": "voltage_source",
    "voltage-source": "voltage_source",
    "vsource": "voltage_source",
}


class _SchematicComponentProtocol(Protocol):
    """Minimal runtime protocol for one schematic component."""

    reference: str
    attributes: dict[str, object]
    ports: list[str] | tuple[str, ...]


class _QschEditorProtocol(Protocol):
    """Minimal runtime protocol for QschEditor-backed services."""

    schematic: object | None
    updated: bool

    def get_components(self, prefixes: str = "*") -> list[str] | tuple[str, ...]:
        """Return component references for the selected prefixes."""

    def get_component(self, reference: str) -> _SchematicComponentProtocol:
        """Return one component object."""

    def get_component_value(self, element: str) -> str:
        """Return one component value."""

    def get_component_parameters(self, element: str) -> dict[object, object]:
        """Return component-local parameter text and parsed values."""

    def get_component_nodes(self, reference: str) -> list[str] | tuple[str, ...]:
        """Return the connected nodes for one component."""

    def get_component_position(self, reference: str) -> tuple[object, object]:
        """Return the position and rotation for one component."""

    def get_subcircuit(self, reference: str) -> _QschEditorProtocol:
        """Return the resolved editor for one subcircuit instance."""

    def add_component(self, component: _SchematicComponentProtocol, **kwargs: object) -> None:
        """Append one component object to the editor."""

    def remove_component(self, reference: str) -> None:
        """Remove one component and its symbol tag from the schematic."""

    def set_component_value(self, reference: str, value: object) -> None:
        """Update one component value."""

    def set_component_position(
        self,
        reference: str,
        position: object,
        rotation: object,
        mirror: bool = False,
    ) -> None:
        """Update one component placement."""

    def set_component_parameters(self, element: str, **kwargs: object) -> None:
        """Update one component parameter set."""

    def set_element_model(self, device: str, model: str) -> None:
        """Update one component model."""

    def set_parameter(self, param: str, value: object) -> None:
        """Update one schematic-level parameter."""

    def add_instruction(self, instruction: str) -> None:
        """Add one directive to the schematic."""

    def remove_instruction(self, instruction: str) -> bool:
        """Remove one matching directive exactly."""

    def remove_Xinstruction(self, search_pattern: str) -> bool:  # noqa: N802
        """Remove directives matching a regular expression."""

    def save_as(self, qsch_filename: str | Path) -> None:
        """Persist the schematic to a `.qsch` file."""


class _QschEditorFactory(Protocol):
    """Callable protocol for constructing a schematic editor instance."""

    def __call__(
        self,
        path: str,
        create_blank: bool = False,
        *,
        workspace_root: Path | None = None,
    ) -> _QschEditorProtocol:
        """Create an editor bound to one schematic path."""


def load_qsch_editor_factory() -> tuple[_QschEditorFactory | None, str | None]:
    """Return the first locally available schematic editor backend."""

    for module_name in _EDITOR_MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        editor_class = getattr(module, "QschEditor", None)
        if editor_class is None:
            continue
        return cast("_QschEditorFactory", editor_class), module_name
    return None, None


def open_schematic_editor(
    raw_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[_QschEditorProtocol, Path, str]:
    """Validate one schematic path and open it through a supported backend."""

    resolved_path = validate_existing_file(
        raw_path, workspace_root=workspace_root, suffixes=(".qsch",)
    )
    editor_factory, backend_name = load_qsch_editor_factory()
    if editor_factory is None or backend_name is None:
        raise BackendUnavailableError(
            "No compatible local QschEditor backend "
            "QschEditor backend is installed for schematic access."
        )
    try:
        editor = editor_factory(
            str(resolved_path),
            workspace_root=workspace_root.resolve(strict=False),
        )
    except Exception as exc:
        raise QSpiceError(
            f"Failed to open schematic data from {resolved_path.name} "
            f"using {backend_name}.QschEditor."
        ) from exc
    return editor, resolved_path, backend_name


def _load_qsch_support_modules() -> tuple[Any, Any]:  # noqa: PLC0415, PLR0915, RUF100
    """Return the QSCH support modules needed to construct new schematic content.

    Returns ``(qsch_module, base_schematic_module)`` where *qsch_module*
    provides ``QschTag`` and the QSCH format constants, and
    *base_schematic_module* provides ``SchematicComponent`` and ``Point``
    factories for constructing new component objects.
    """

    from qspice_mcp.services._backends._qsch_support import (  # noqa: PLC0415
        QSCH_COMPONENT_POS,
        QSCH_COMPONENT_ROTATION,
        QSCH_SYMBOL_PIN_NET,
        QSCH_SYMBOL_PIN_NET_BEHAVIORAL,
        QSCH_SYMBOL_PIN_POS1,
        QSCH_SYMBOL_PIN_POS2,
        QSCH_SYMBOL_TEXT_REFDES,
        QSCH_SYMBOL_TEXT_VALUE,
        QSCH_TEXT_COLOR,
        QSCH_TEXT_COMMENT,
        QSCH_TEXT_INSTR_QUALIFIER,
        QSCH_TEXT_POS,
        QSCH_TEXT_ROTATION,
        QSCH_TEXT_SIZE,
        QSCH_TEXT_STR_ATTR,
    )
    from qspice_mcp.services._backends._qsch_support import (  # noqa: PLC0415
        QschTag as _QschTag,
    )

    # Build lightweight module-like objects with the expected attribute names.
    _qsch_module = type(
        "_QschModule",
        (),
        {
            "QschTag": _QschTag,
            "QSCH_COMPONENT_POS": QSCH_COMPONENT_POS,
            "QSCH_COMPONENT_ROTATION": QSCH_COMPONENT_ROTATION,
            "QSCH_SYMBOL_PIN_NET": QSCH_SYMBOL_PIN_NET,
            "QSCH_SYMBOL_PIN_NET_BEHAVIORAL": QSCH_SYMBOL_PIN_NET_BEHAVIORAL,
            "QSCH_SYMBOL_PIN_POS1": QSCH_SYMBOL_PIN_POS1,
            "QSCH_SYMBOL_PIN_POS2": QSCH_SYMBOL_PIN_POS2,
            "QSCH_SYMBOL_TEXT_REFDES": QSCH_SYMBOL_TEXT_REFDES,
            "QSCH_SYMBOL_TEXT_VALUE": QSCH_SYMBOL_TEXT_VALUE,
            "QSCH_TEXT_COLOR": QSCH_TEXT_COLOR,
            "QSCH_TEXT_COMMENT": QSCH_TEXT_COMMENT,
            "QSCH_TEXT_INSTR_QUALIFIER": QSCH_TEXT_INSTR_QUALIFIER,
            "QSCH_TEXT_POS": QSCH_TEXT_POS,
            "QSCH_TEXT_ROTATION": QSCH_TEXT_ROTATION,
            "QSCH_TEXT_SIZE": QSCH_TEXT_SIZE,
            "QSCH_TEXT_STR_ATTR": QSCH_TEXT_STR_ATTR,
        },
    )()

    _qsch_module = type(
        "_QschModule",
        (),
        {
            "QschTag": _QschTag,
            "QSCH_COMPONENT_POS": QSCH_COMPONENT_POS,
            "QSCH_COMPONENT_ROTATION": QSCH_COMPONENT_ROTATION,
            "QSCH_SYMBOL_PIN_NET": QSCH_SYMBOL_PIN_NET,
            "QSCH_SYMBOL_PIN_NET_BEHAVIORAL": QSCH_SYMBOL_PIN_NET_BEHAVIORAL,
            "QSCH_SYMBOL_PIN_POS1": QSCH_SYMBOL_PIN_POS1,
            "QSCH_SYMBOL_PIN_POS2": QSCH_SYMBOL_PIN_POS2,
            "QSCH_SYMBOL_TEXT_REFDES": QSCH_SYMBOL_TEXT_REFDES,
            "QSCH_SYMBOL_TEXT_VALUE": QSCH_SYMBOL_TEXT_VALUE,
            "QSCH_TEXT_COLOR": QSCH_TEXT_COLOR,
            "QSCH_TEXT_COMMENT": QSCH_TEXT_COMMENT,
            "QSCH_TEXT_INSTR_QUALIFIER": QSCH_TEXT_INSTR_QUALIFIER,
            "QSCH_TEXT_POS": QSCH_TEXT_POS,
            "QSCH_TEXT_ROTATION": QSCH_TEXT_ROTATION,
            "QSCH_TEXT_SIZE": QSCH_TEXT_SIZE,
            "QSCH_TEXT_STR_ATTR": QSCH_TEXT_STR_ATTR,
        },
    )()

    def _point_init(self: object, x: int, y: int) -> None:
        self.X = x  # type: ignore[attr-defined]
        self.Y = y  # type: ignore[attr-defined]

    _point = type(
        "Point",
        (),
        {
            "__slots__": ("X", "Y"),
            "__init__": _point_init,
            "__repr__": lambda self: f"Point({self.X}, {self.Y})",
        },
    )

    def _make_schematic_component(editor: object, reference: str) -> object:
        comp = type("_SchematicComponent", (), {})()
        comp.reference = reference
        comp.position = _point(0, 0)
        comp.rotation = 0
        comp.attributes = {}
        return comp

    _base_schematic_module = type(
        "_BaseSchematicModule",
        (),
        {
            "Point": _point,
            "SchematicComponent": staticmethod(_make_schematic_component),
        },
    )()

    return _qsch_module, _base_schematic_module


def supported_simple_component_kinds() -> tuple[str, ...]:
    """Return canonical ``add_component`` kinds in stable sorted order."""

    return tuple(sorted(set(_SIMPLE_COMPONENT_KIND_ALIASES.values())))


def _normalize_component_kind(component_kind: str) -> SimpleComponentKind:
    """Normalize one simple component-kind token."""

    normalized = component_kind.strip().lower()
    try:
        return _SIMPLE_COMPONENT_KIND_ALIASES[normalized]
    except KeyError as exc:
        supported = ", ".join(supported_simple_component_kinds())
        raise ValueError(
            f"Unsupported component_kind: {component_kind}. Supported kinds: {supported}"
        ) from exc


def _quote_qsch_string(value: str) -> str:
    """Quote one text token for QSch tags."""

    if '"' in value:
        raise ValueError("QSch text tokens must not contain double quotes.")
    return f'"{value}"'


def _unquote_qsch_string(value: str) -> str:
    """Remove one matching pair of surrounding QSch string quotes."""

    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _normalize_net_name(net_name: str) -> str:
    """Normalize one user-supplied net name."""

    normalized = net_name.strip()
    if not normalized:
        raise ValueError("net_name must not be empty.")
    return normalized


def _normalize_pin_name(pin_name: str) -> str:
    """Normalize one user-supplied pin name."""

    normalized = pin_name.strip()
    if not normalized:
        raise ValueError("pin_name must not be empty.")
    return normalized


def _format_qsch_point(position: tuple[int, int]) -> str:
    """Format one integer point as a QSch coordinate token."""

    return f"({position[0]},{position[1]})"


def _normalize_qsch_color_code(token: object) -> str:
    """Normalize one raw QSch color token into a stable hex-like string."""

    raw_token = str(token).strip()
    if raw_token.lower().startswith("0x"):
        return raw_token.lower()
    try:
        return f"0x{int(raw_token):x}"
    except ValueError:
        return raw_token


def _coerce_qsch_color_code(value: str | int) -> str:
    """Coerce one user-supplied color value into a QSch-compatible token."""

    if isinstance(value, int):
        return f"0x{value:x}"
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("color_code must not be empty.")
    if normalized.startswith("0x"):
        return normalized
    try:
        return f"0x{int(normalized):x}"
    except ValueError as exc:
        raise ValueError("color_code must be an integer or 0x-prefixed string.") from exc


def _normalize_optional_bool(value: object) -> bool | None:
    """Normalize one optional QSch boolean-like token."""

    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def resolve_schematic_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
) -> Path:
    """Resolve an optional schematic output path inside the workspace root."""

    if output_path is None:
        return default.resolve(strict=False)
    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() != ".qsch":
        raise ValueError("Schematic output path must end in .qsch")
    return resolved


def normalize_component_parameters(
    raw_parameters: dict[object, object],
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Normalize component parameter output."""

    parameters: dict[str, str] = {}
    raw_lines: list[tuple[int, str]] = []
    for key, value in raw_parameters.items():
        if isinstance(key, str):
            parameters[key] = str(value)
        elif isinstance(key, int):
            raw_lines.append((key, str(value)))
    raw_lines.sort(key=lambda item: item[0])
    return parameters, tuple(value for _, value in raw_lines)


def normalize_component_position(position: object) -> tuple[int, int]:
    """Normalize one schematic point-like object to integer coordinates."""

    if isinstance(position, tuple) and len(position) == _POINT_COORDINATE_COUNT:
        return int(position[0]), int(position[1])
    if hasattr(position, "X") and hasattr(position, "Y"):
        return int(position.X), int(position.Y)
    if hasattr(position, "x") and hasattr(position, "y"):
        return int(position.x), int(position.y)
    raise ValueError(f"Unsupported schematic position object: {position!r}")


def component_rotation_degrees_to_index(degrees: int) -> int:
    """Convert QSPICE component rotation degrees to the on-disk rotation index."""

    if degrees % _ROTATION_STEP_DEGREES != 0:
        raise ValueError(
            f"rotation_degrees must be a multiple of {_ROTATION_STEP_DEGREES}, got {degrees}."
        )
    rotation_index = degrees // _ROTATION_STEP_DEGREES
    if rotation_index < 0 or rotation_index > _ROTATION_INDEX_MAX:
        max_degrees = _ROTATION_INDEX_MAX * _ROTATION_STEP_DEGREES
        raise ValueError(
            f"rotation_degrees {degrees} is outside the supported 0-{max_degrees} range."
        )
    return rotation_index


def component_rotation_index_to_degrees(rotation_index: int) -> int:
    """Convert one QSPICE component rotation index to degrees."""

    if rotation_index < 0 or rotation_index > _MIRROR_ROTATION_INDEX_MAX:
        raise ValueError(f"Unsupported component rotation index: {rotation_index}")
    if rotation_index <= _ROTATION_INDEX_MAX:
        return rotation_index * _ROTATION_STEP_DEGREES
    return (rotation_index - _MIRROR_ROTATION_OFFSET) * _ROTATION_STEP_DEGREES


def normalize_component_rotation(rotation: object) -> int:
    """Normalize one schematic rotation object to degrees."""

    if isinstance(rotation, (int, float)):
        rotation_index = int(rotation)
    elif hasattr(rotation, "value"):
        value = rotation.value
        if not isinstance(value, (int, float)):
            raise TypeError(f"Unsupported schematic rotation object: {rotation!r}")
        rotation_index = int(value)
    else:
        raise ValueError(f"Unsupported schematic rotation object: {rotation!r}")
    return component_rotation_index_to_degrees(rotation_index)
