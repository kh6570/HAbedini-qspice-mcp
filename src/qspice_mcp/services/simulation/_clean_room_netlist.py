"""Conservative clean-room qsch-to-netlist regeneration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import QSpiceError

if TYPE_CHECKING:
    from pathlib import Path

Coordinate = tuple[int, int]

_COMPONENT_PATTERN = re.compile(r"component \((-?\d+),(-?\d+)\)\s+(-?\d+)\s+(-?\d+)")
_PIN_PATTERN = re.compile(r'pin \((-?\d+),(-?\d+)\) \((-?\d+),(-?\d+)\) .*?"([^"]+)"')
_WIRE_PATTERN = re.compile(r'wire \((-?\d+),(-?\d+)\) \((-?\d+),(-?\d+)\)(?:\s+"([^"]*)")?')
_NET_PATTERN = re.compile(r'net \((-?\d+),(-?\d+)\) .*?"([^"]+)"')
_JUNCTION_PATTERN = re.compile(r"junction \((-?\d+),(-?\d+)\)")
_QUOTED_TEXT_PATTERN = re.compile(r'"([^"]*)"')
_ANALYSIS_PREFIXES = (".ac", ".dc", ".noise", ".op", ".tf", ".tran", ".step")
_TOP_LEVEL_PREFIXES = ("component ", "wire ", "net ", "junction ", "text ")
_ATTRIBUTE_TEXT_START_INDEX = 2
_MIN_CONNECTED_POINTS = 2
_MOS_THREE_PIN_COUNT = 3
_MOS_FOUR_PIN_COUNT = 4
_DIODE_LIBRARY_FILE = "Diode.txt"
_NMOS_LIBRARY_FILE = "NMOS.txt"
_PMOS_LIBRARY_FILE = "PMOS.txt"
_REFERENCE_TOKEN_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_:.\-$]*$")

# Component types that QSPICE handles through the schematic but cannot be
# represented in a standard SPICE netlist.  The clean-room renderer skips
# them so the generated .net stays simulation-ready.
_DLL_SYMBOL_TOKENS = frozenset({".dll", "(.dll)", "ø(.dll)", "c-block", "verilog"})


@dataclass(frozen=True, slots=True)
class _Pin:
    order: int
    name: str
    point: Coordinate


@dataclass(frozen=True, slots=True)
class _Wire:
    start: Coordinate
    end: Coordinate
    name: str | None = None


@dataclass(frozen=True, slots=True)
class _NetLabel:
    point: Coordinate
    name: str


@dataclass(slots=True)
class _ComponentAccumulator:
    indent: int
    anchor: Coordinate
    rotation_code: int
    mirror_code: int
    symbol: str = "unknown"
    kind: str = "unknown"
    description: str | None = None
    texts: list[str] = field(default_factory=list)
    pins: list[tuple[int, int, str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _Component:
    reference: str | None
    kind: str
    symbol: str
    value: str | None
    description: str | None
    attributes: tuple[str, ...]
    pins: tuple[_Pin, ...]
    anchor: Coordinate
    rotation_code: int
    mirror_code: int


@dataclass(frozen=True, slots=True)
class ParsedCleanRoomNetlist:
    netlist_text: str
    component_count: int
    directive_count: int


ParsedSchematic = tuple[
    tuple[_Component, ...],
    tuple[_Wire, ...],
    tuple[_NetLabel, ...],
    tuple[str, ...],
]


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[Coordinate, Coordinate] = {}

    def add(self, point: Coordinate) -> None:
        self._parent.setdefault(point, point)

    def find(self, point: Coordinate) -> Coordinate:
        parent = self._parent.setdefault(point, point)
        if parent != point:
            parent = self.find(parent)
            self._parent[point] = parent
        return parent

    def union(self, left: Coordinate, right: Coordinate) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self._parent[right_root] = left_root


def _decode_qsch_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeError:
            continue
        if "schematic" in text.lower():
            return text
    return raw_bytes.decode("utf-8", errors="replace")


def _normalize_line(raw_line: str) -> tuple[int, str]:
    cleaned = raw_line.replace("\ufeff", "").replace("\x00", "")
    cleaned = re.sub(r"(^\s*)\ufffd", r"\1", cleaned)
    cleaned = re.sub(r"\ufffd\s*$", "", cleaned)
    indent = len(cleaned) - len(cleaned.lstrip())
    return indent, cleaned.strip()


def _extract_quoted_text(line: str) -> str | None:
    match = _QUOTED_TEXT_PATTERN.search(line)
    if match is None:
        return None
    return match.group(1).replace("\ufffd", "u").replace("µ", "u").replace("μ", "u")


def _transform_point(
    point: Coordinate,
    *,
    anchor: Coordinate,
    rotation_code: int,
    mirror_code: int,
) -> Coordinate:
    if rotation_code % 2 != 0:
        raise QSpiceError(
            f"Unsupported qsch component rotation code {rotation_code}; expected quarter turns."
        )
    if mirror_code not in {0, 1, 2, 3}:
        raise QSpiceError(
            f"Unsupported qsch mirror code {mirror_code}; expected one of 0, 1, 2, or 3."
        )
    x, y = point
    for _ in range((rotation_code // 2) % 4):
        x, y = -y, x
    if mirror_code in {1, 3}:
        x = -x
    if mirror_code in {2, 3}:
        y = -y
    return (anchor[0] + x, anchor[1] + y)


def _reference_prefixes(*, symbol: str, kind: str) -> tuple[str, ...]:
    prefixes: list[str] = []
    for candidate in (kind.upper(), symbol.upper()):
        if candidate in {"MN", "MP", "NMOS", "PMOS"}:
            prefix = "M"
        elif candidate:
            prefix = candidate[0]
        else:
            continue
        if prefix not in prefixes:
            prefixes.append(prefix)
    return tuple(prefixes)


def _looks_like_reference(text: str, *, symbol: str, kind: str) -> bool:
    normalized = text.strip()
    if not normalized or _REFERENCE_TOKEN_PATTERN.fullmatch(normalized) is None:
        return False
    uppercase = normalized.upper()
    for prefix in _reference_prefixes(symbol=symbol, kind=kind):
        if uppercase.startswith(prefix) and any(
            character.isdigit() for character in uppercase[len(prefix) :]
        ):
            return True
    return False


def _resolve_component_texts(
    current: _ComponentAccumulator,
) -> tuple[str | None, str | None, tuple[str, ...]]:
    texts = [text.strip() for text in current.texts if text.strip()]
    if not texts:
        return None, None, ()

    reference_index = next(
        (
            index
            for index, text in enumerate(texts)
            if _looks_like_reference(text, symbol=current.symbol, kind=current.kind)
        ),
        0,
    )
    reference = texts.pop(reference_index)

    value_index = next(
        (index for index, text in enumerate(texts) if "=" not in text and not text.startswith(".")),
        None,
    )
    value = None if value_index is None else texts.pop(value_index)
    return reference, value, tuple(texts)


def _finalize_component(
    components: list[_Component],
    current: _ComponentAccumulator | None,
) -> None:
    if current is None:
        return
    reference, value, attributes = _resolve_component_texts(current)
    pins = tuple(
        _Pin(
            order=index,
            name=name,
            point=_transform_point(
                (relative_x, relative_y),
                anchor=current.anchor,
                rotation_code=current.rotation_code,
                mirror_code=current.mirror_code,
            ),
        )
        for index, (relative_x, relative_y, name) in enumerate(current.pins)
    )
    components.append(
        _Component(
            reference=reference,
            kind=current.kind,
            symbol=current.symbol,
            value=value,
            description=current.description,
            attributes=attributes,
            pins=pins,
            anchor=current.anchor,
            rotation_code=current.rotation_code,
            mirror_code=current.mirror_code,
        )
    )


def _parse_qsch_schematic(  # noqa: PLR0912, PLR0915
    schematic_path: Path,
    *,
    allow_empty: bool = False,
) -> ParsedSchematic:
    lines = tuple(
        _normalize_line(line)
        for line in _decode_qsch_text(schematic_path.read_bytes()).splitlines()
    )
    components: list[_Component] = []
    wires: list[_Wire] = []
    nets: list[_NetLabel] = []
    directives: list[str] = []
    junctions: list[Coordinate] = []
    current: _ComponentAccumulator | None = None

    for indent, line in lines:
        if not line:
            continue
        text_value = _extract_quoted_text(line) if line.startswith("text ") else None
        if current is not None and (
            line.startswith("component ")
            or line.startswith("wire ")
            or line.startswith("net ")
            or line.startswith("junction ")
            or (
                line.startswith("text ")
                and (indent <= current.indent or (text_value or "").startswith("."))
            )
        ):
            _finalize_component(components, current)
            current = None

        if line.startswith("component "):
            _finalize_component(components, current)
            current = None
            component_match = _COMPONENT_PATTERN.fullmatch(line)
            if component_match is None:
                raise QSpiceError(f"Unsupported qsch component header: {line}")
            current = _ComponentAccumulator(
                indent=indent,
                anchor=(int(component_match.group(1)), int(component_match.group(2))),
                rotation_code=int(component_match.group(3)),
                mirror_code=int(component_match.group(4)),
            )
            continue

        if current is not None:
            if line.startswith("symbol "):
                current.symbol = line.removeprefix("symbol ").strip()
                continue
            if line.startswith("type:"):
                current.kind = line.partition(":")[2].strip()
                continue
            if line.startswith("description:"):
                current.description = line.partition(":")[2].strip() or None
                continue
            if line.startswith("text "):
                value = text_value
                if value is not None:
                    current.texts.append(value)
                continue
            if line.startswith("pin "):
                pin_match = _PIN_PATTERN.fullmatch(line)
                if pin_match is None:
                    raise QSpiceError(f"Unsupported qsch pin definition: {line}")
                current.pins.append(
                    (int(pin_match.group(1)), int(pin_match.group(2)), pin_match.group(5))
                )
                continue
            continue

        if line.startswith("wire "):
            wire_match = _WIRE_PATTERN.fullmatch(line)
            if wire_match is None:
                raise QSpiceError(f"Unsupported qsch wire definition: {line}")
            wires.append(
                _Wire(
                    start=(int(wire_match.group(1)), int(wire_match.group(2))),
                    end=(int(wire_match.group(3)), int(wire_match.group(4))),
                    name=wire_match.group(5),
                )
            )
            continue
        if line.startswith("net "):
            net_match = _NET_PATTERN.fullmatch(line)
            if net_match is None:
                raise QSpiceError(f"Unsupported qsch net label definition: {line}")
            nets.append(
                _NetLabel(
                    point=(int(net_match.group(1)), int(net_match.group(2))),
                    name=net_match.group(3),
                )
            )
            continue
        if line.startswith("junction "):
            junction_match = _JUNCTION_PATTERN.fullmatch(line)
            if junction_match is None:
                raise QSpiceError(f"Unsupported qsch junction definition: {line}")
            junctions.append((int(junction_match.group(1)), int(junction_match.group(2))))
            continue
        if line.startswith("text "):
            value = _extract_quoted_text(line)
            if value is not None and value.startswith("."):
                directives.append(value)

    _finalize_component(components, current)

    if not components and not allow_empty:
        raise QSpiceError("No qsch components were found in the schematic text.")

    all_nets: tuple[_NetLabel, ...] = (
        *nets,
        *(_NetLabel(point=point, name="") for point in junctions),
    )
    return tuple(components), tuple(wires), all_nets, tuple(directives)


def _point_on_segment(point: Coordinate, start: Coordinate, end: Coordinate) -> bool:
    cross_product = (point[1] - start[1]) * (end[0] - start[0]) - (point[0] - start[0]) * (
        end[1] - start[1]
    )
    if cross_product != 0:
        return False
    return min(start[0], end[0]) <= point[0] <= max(start[0], end[0]) and min(
        start[1], end[1]
    ) <= point[1] <= max(start[1], end[1])


def _normalize_net_name(name: str) -> str:
    normalized = name.strip()
    if normalized.upper() == "GND" or normalized == "0":
        return "0"
    return normalized


def _build_net_names(  # noqa: PLR0912
    components: tuple[_Component, ...],
    wires: tuple[_Wire, ...],
    nets: tuple[_NetLabel, ...],
) -> dict[Coordinate, str]:
    union_find = _UnionFind()
    candidate_points: set[Coordinate] = set()
    for component in components:
        for pin in component.pins:
            candidate_points.add(pin.point)
    for wire in wires:
        candidate_points.add(wire.start)
        candidate_points.add(wire.end)
    for net in nets:
        candidate_points.add(net.point)

    for point in candidate_points:
        union_find.add(point)

    for wire in wires:
        on_segment = [
            point for point in candidate_points if _point_on_segment(point, wire.start, wire.end)
        ]
        if len(on_segment) < _MIN_CONNECTED_POINTS:
            continue
        root_point = on_segment[0]
        for point in on_segment[1:]:
            union_find.union(root_point, point)

    named_roots: dict[Coordinate, set[str]] = {}
    for wire in wires:
        if wire.name is None or not wire.name.strip():
            continue
        root = union_find.find(wire.start)
        named_roots.setdefault(root, set()).add(_normalize_net_name(wire.name))
    for net in nets:
        if not net.name.strip():
            continue
        root = union_find.find(net.point)
        named_roots.setdefault(root, set()).add(_normalize_net_name(net.name))

    root_to_name: dict[Coordinate, str] = {}
    unnamed_index = 1
    for component in components:
        for pin in component.pins:
            root = union_find.find(pin.point)
            if root in root_to_name:
                continue
            labels = named_roots.get(root, set())
            if len(labels) > 1:
                normalized = {label.upper() for label in labels}
                hint = ""
                if normalized & {"0", "GND"} and normalized - {"0", "GND"}:
                    hint = (
                        " A spanning GND wire may pass through a component pin "
                        "(for example the bottom pin of a vertical R/C); use "
                        "separate GND symbols at V- and the load instead."
                    )
                raise QSpiceError(
                    "Conflicting qsch net labels were found on the same "
                    f"connection: {sorted(labels)}.{hint}"
                )
            if labels:
                root_to_name[root] = next(iter(labels))
            else:
                root_to_name[root] = f"N{unnamed_index:03d}"
                unnamed_index += 1
    point_to_name: dict[Coordinate, str] = {}
    for component in components:
        for pin in component.pins:
            point_to_name[pin.point] = root_to_name[union_find.find(pin.point)]
    return point_to_name


def _render_component_line(component: _Component, net_names: dict[Coordinate, str]) -> str | None:
    reference = component.reference
    if reference is None:
        return None
    symbol = component.symbol.upper()
    kind = component.kind.upper()
    if symbol in {"G", "GROUND"} or kind in {"G", "GROUND"}:
        return None
    if _is_dll_component(component):
        return None

    nodes = [net_names[pin.point] for pin in sorted(component.pins, key=lambda pin: pin.order)]
    tokens = [reference, *nodes]
    if symbol in {"NMOS", "PMOS"} or kind in {"MN", "MP"}:
        if component.value is None:
            raise QSpiceError(f"MOS component {reference} is missing its model name.")
        if len(nodes) == _MOS_THREE_PIN_COUNT:
            tokens.append(nodes[2])
        elif len(nodes) != _MOS_FOUR_PIN_COUNT:
            raise QSpiceError(
                f"MOS component {reference} requires three or four connected "
                f"pins, found {len(nodes)}."
            )
        tokens.append(component.value)
        tokens.extend(component.attributes)
        return " ".join(tokens)

    if component.value is not None:
        tokens.append(component.value)
    tokens.extend(component.attributes)
    if len(tokens) <= 1 + len(nodes):
        raise QSpiceError(
            f"Component {reference} is missing the value or model token needed "
            "for netlist regeneration."
        )
    return " ".join(tokens)


def _is_dll_component(component: _Component) -> bool:
    """Return True when a component is a DLL, Verilog, or C-block type that cannot
    be represented in a standard SPICE netlist and must be skipped."""
    symbol_lower = component.symbol.lower().replace("\ufffd", "").strip()
    kind_lower = component.kind.lower().replace("\ufffd", "").strip()
    for token in (symbol_lower, kind_lower):
        # Strip common noise: replacement chars, Norwegian Ø, parentheses, whitespace
        cleaned = token.replace("ø", "").strip("() ").strip()
        if cleaned in _DLL_SYMBOL_TOKENS:
            return True
        # Also match when the token contains a known DLL marker
        if ".dll" in cleaned or "verilog" in cleaned or "c-block" in cleaned:
            return True
    return False


def _required_library_file(component: _Component) -> str | None:
    symbol = component.symbol.upper()
    kind = component.kind.upper()
    if symbol == "NMOS" or kind == "MN":
        return _NMOS_LIBRARY_FILE
    if symbol == "PMOS" or kind == "MP":
        return _PMOS_LIBRARY_FILE
    if symbol in {"D", "DIODE"} or kind in {"D", "DIODE"}:
        return _DIODE_LIBRARY_FILE
    return None


def _required_library_directives(components: tuple[_Component, ...]) -> tuple[str, ...]:
    library_files: list[str] = []
    for component in components:
        library_file = _required_library_file(component)
        if library_file is None or library_file in library_files:
            continue
        library_files.append(library_file)
    return tuple(f".lib {library_file}" for library_file in library_files)


def dll_component_references(schematic_path: Path) -> tuple[str, ...]:
    """Return schematic reference designators for DLL, Verilog, or C-block components."""

    try:
        components, _, _, _ = _parse_qsch_schematic(schematic_path)
    except QSpiceError:
        return ()
    references: list[str] = []
    for component in components:
        if component.reference is None or not _is_dll_component(component):
            continue
        references.append(component.reference)
    return tuple(references)


def netlist_covers_dll_references(netlist_text: str, references: tuple[str, ...]) -> bool:
    """Return whether a derived netlist includes instance lines for every DLL reference."""

    if not references:
        return True
    remaining = set(references)
    for line in netlist_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        remaining.discard(stripped.split(maxsplit=1)[0])
        if not remaining:
            return True
    return False


def render_clean_room_netlist(schematic_path: Path) -> ParsedCleanRoomNetlist:
    components, wires, nets, directives = _parse_qsch_schematic(schematic_path)
    net_names = _build_net_names(components, wires, nets)
    library_directives = _required_library_directives(components)
    component_lines = [
        rendered
        for rendered in (_render_component_line(component, net_names) for component in components)
        if rendered is not None
    ]
    if not component_lines:
        raise QSpiceError(
            "The qsch schematic did not contain any supported netlist-bearing components."
        )

    prelude_directives = [
        directive
        for directive in directives
        if not directive.lower().startswith(_ANALYSIS_PREFIXES)
    ]
    analysis_directives = [
        directive for directive in directives if directive.lower().startswith(_ANALYSIS_PREFIXES)
    ]
    lines = [
        f"* {schematic_path.name}",
        *prelude_directives,
        *component_lines,
        *library_directives,
        *analysis_directives,
        ".end",
    ]
    return ParsedCleanRoomNetlist(
        netlist_text="\n".join(lines) + "\n",
        component_count=len(component_lines),
        directive_count=len(directives),
    )


__all__ = [
    "ParsedCleanRoomNetlist",
    "dll_component_references",
    "netlist_covers_dll_references",
    "render_clean_room_netlist",
]
