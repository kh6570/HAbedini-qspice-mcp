"""Repo-owned QschEditor — parses, indexes, mutates, and persists .qsch files.

Provides the ``QschEditor`` class that satisfies ``_QschEditorProtocol``
using only the repo-owned ``_qsch_support.QschTag`` tree as its internal
representation.  No third-party schematic packages are required.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services._backends._qsch_support import (
    QSCH_COMPONENT_POS,
    QSCH_COMPONENT_ROTATION,
    QSCH_SYMBOL_PIN_NET,
    QSCH_SYMBOL_PIN_NET_BEHAVIORAL,
    QSCH_TEXT_INSTR_QUALIFIER,
    QSCH_TEXT_STR_ATTR,
    QschTag,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Binary file magic / encoding
# ---------------------------------------------------------------------------

_QSCH_BINARY_PREFIX = b"\xff\xd8\xff\xdb"
_QOPEN = "\u00ab"  # «
_QCLOSE = "\u00bb"  # »


def _decode_qsch_bytes(raw_bytes: bytes) -> str:
    """Decode .qsch file bytes using QSPICE's Latin-1 wire format.

    QSPICE .qsch files are Latin-1, with guillemets as single bytes
    ``\\xab``/``\\xbb``.  Inline UTF-8 BOM byte sequences may appear
    before analysis directives; strip those qualifiers before decoding.
    Do not attempt whole-file UTF-8 decoding: valid UTF-8 byte runs can
    mis-decode Latin-1 guillemets into non-cp1252 characters.
    """
    # Strip UTF-8 BOM bytes if present (they appear before directives)
    raw_bytes = raw_bytes.replace(b"\xef\xbb\xbf", b"")
    # Latin-1 preserves the \xab/\xbb guillemet bytes as «/»
    return raw_bytes.decode("latin-1")


def _split_qsch_tokens(line: str) -> list[str]:
    """Split a QSCH tag's inner content into tokens, respecting double-quoted strings."""
    tokens: list[str] = []
    current: list[str] = []
    in_quotes = False
    for ch in line:
        if ch == '"':
            in_quotes = not in_quotes
            current.append(ch)
        elif ch in (" ", "\t") and not in_quotes:
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


# ---------------------------------------------------------------------------
# Tag-level constants
# ---------------------------------------------------------------------------

_TAG_COMPONENT = "component"
_TAG_SYMBOL = "symbol"
_TAG_TEXT = "text"
_TAG_WIRE = "wire"
_TAG_NET = "net"
_TAG_SCHEMATIC = "schematic"

# ---------------------------------------------------------------------------
# Pattern helpers
# ---------------------------------------------------------------------------

_COMPONENT_HEADER_PATTERN = re.compile(r"^component \((-?\d+),(-?\d+)\) (\d+) (\d+)$")
_QUOTED_VALUE_PATTERN = re.compile(r'"([^"]*)"')
_REFERENCE_PATTERN = re.compile(r"^([A-Za-z]+\d+)$")


# ---------------------------------------------------------------------------
# Internal data classes
# ---------------------------------------------------------------------------


class _SchematicComponent:
    """Lightweight component object matching ``_SchematicComponentProtocol``."""

    __slots__ = ("attributes", "ports", "position", "reference", "rotation")

    def __init__(self, reference: str) -> None:
        self.reference = reference
        self.attributes: dict[str, Any] = {}
        self.ports: list[str] = []
        self.position: Any = _Point(0, 0)
        self.rotation: int = 0

    def __repr__(self) -> str:
        return f"_SchematicComponent({self.reference!r})"


class _Point:  # noqa: PLW1641
    """Lightweight 2-D point matching spicelib's ``Point`` shape."""

    __slots__ = ("X", "Y")

    def __init__(self, x: int, y: int) -> None:
        self.X = x
        self.Y = y

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _Point):
            return bool(self.X == other.X and self.Y == other.Y)
        if isinstance(other, (tuple, list)) and len(other) == 2:  # noqa: PLR2004
            return bool(other[0] == self.X and other[1] == self.Y)
        return NotImplemented

    def __repr__(self) -> str:
        return f"Point({self.X}, {self.Y})"


# ---------------------------------------------------------------------------
# QschEditor
# ---------------------------------------------------------------------------


class QschEditor:
    """Repo-owned schematic editor for .qsch files.

    Parses the QschTag tree on construction, indexes components by
    reference, and writes back the full tree on :meth:`save_as`.
    """

    __slots__ = ("_components", "_instructions", "_path", "_root", "_workspace_root", "updated")

    def __init__(
        self,
        path: str,
        create_blank: bool = False,
        *,
        workspace_root: Path | None = None,
    ) -> None:
        from pathlib import Path as _Path  # noqa: PLC0415

        self._path = path
        self._workspace_root = (
            workspace_root.resolve(strict=False)
            if workspace_root is not None
            else _Path(path).resolve(strict=False).parent
        )
        self._components: dict[str, tuple[QschTag, QschTag]] = {}
        self._instructions: list[tuple[QschTag, int]] = []
        self.updated: bool = False

        if create_blank:
            self._root = QschTag(_TAG_SCHEMATIC)
            return

        raw_bytes: bytes
        try:
            with open(path, "rb") as fh:  # noqa: PTH123
                raw_bytes = fh.read()
        except FileNotFoundError as exc:
            raise QSpiceError(f"Schematic file not found: {path}") from exc
        except OSError as exc:
            raise QSpiceError(f"Cannot read schematic file {path}: {exc}") from exc

        # Strip optional JPEG-like binary prefix
        if raw_bytes.startswith(_QSCH_BINARY_PREFIX):
            raw_bytes = raw_bytes[4:]

        text = _decode_qsch_bytes(raw_bytes)
        text = text.replace("\x00", "")

        # Parse the tag tree
        self._root, _consumed = self._parse_tree(text, 0)
        if self._root.tag != _TAG_SCHEMATIC:
            self._root = QschTag(_TAG_SCHEMATIC)

        self._index()

    # ------------------------------------------------------------------
    # Internal: parse & index  # noqa: ERA001
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tree(stream: str, start: int) -> tuple[QschTag, int]:  # noqa: PLR0912
        """Parse one QschTag and its children from *stream*[start:].

        Returns ``(tag, consumed)``.  The QSCH format uses line-oriented
        structure: each ``«tag ...`` line opens a tag; a lone ``»``
        (possibly indented) closes the innermost open tag.
        """
        # Find the next «
        pos = start
        while pos < len(stream) and stream[pos] != _QOPEN:
            pos += 1
        if pos >= len(stream):
            return QschTag(""), pos - start

        tag_start = pos  # noqa: F841
        # Find end of the opening line
        nl = stream.find("\n", pos)
        if nl == -1:
            nl = len(stream)
        line = stream[pos:nl].rstrip("\r")
        pos = nl + 1  # advance past \n

        # Strip « prefix
        inner = line[1:] if line.startswith(_QOPEN) else line

        if inner.endswith(_QCLOSE):
            # Leaf (self-closing) tag
            inner = inner[:-1]  # strip trailing »
            tokens = _split_qsch_tokens(inner)
            if not tokens:
                return QschTag(""), pos - start
            tag = QschTag(tokens[0], *tokens[1:])
            return tag, pos - start

        # Parent tag — tokens from the opening line
        tokens = _split_qsch_tokens(inner)
        if not tokens:
            return QschTag(""), pos - start
        tag = QschTag(tokens[0], *tokens[1:])

        # Parse children until the closing »
        while pos < len(stream):
            # Find the next significant character
            while pos < len(stream) and stream[pos] in (" ", "\t", "\r", "\n"):
                pos += 1
            if pos >= len(stream):
                break

            if stream[pos] == _QCLOSE:
                # Closing » — consume this line and stop
                nl2 = stream.find("\n", pos)
                pos = (nl2 + 1) if nl2 != -1 else len(stream)
                break
            if stream[pos] == _QOPEN:
                # Child tag
                child, child_consumed = QschEditor._parse_tree(stream, pos)
                if child.tag:
                    tag.items.append(child)
                pos += child_consumed
            else:
                pos += 1

        return tag, pos - start

    def _index(self) -> None:
        """Walk the tag tree and index components + instructions."""
        self._components.clear()
        self._instructions.clear()

        for item in self._root.items:
            if item.tag == _TAG_COMPONENT:
                ref = self._extract_reference(item)
                if ref:
                    # Find the symbol sub-tag
                    symbol_tag = None
                    for child in item.items:
                        if child.tag == _TAG_SYMBOL:
                            symbol_tag = child
                            break
                    self._components[ref] = (item, symbol_tag or item)
            elif item.tag == _TAG_TEXT:
                text_val = self._get_text_value(item)
                if text_val is not None and (
                    text_val.startswith(".") or text_val.startswith(QSCH_TEXT_INSTR_QUALIFIER)
                ):
                    self._instructions.append((item, len(self._instructions)))

    @staticmethod
    def _extract_reference(component_tag: QschTag) -> str | None:
        """Find the REFDES text inside a component's symbol child."""
        symbol: QschTag | None = None
        for child in component_tag.items:
            if child.tag == _TAG_SYMBOL:
                symbol = child
                break
        if symbol is None:
            return None
        for text_tag in symbol.items:
            if text_tag.tag != _TAG_TEXT:
                continue
            val = QschEditor._get_text_value(text_tag)
            if val and _REFERENCE_PATTERN.match(val):
                return val
        return None

    @staticmethod
    def _get_text_value(text_tag: QschTag) -> str | None:
        """Return the quoted string value from a text tag, if present."""
        if len(text_tag.tokens) > QSCH_TEXT_STR_ATTR:
            val = text_tag.tokens[QSCH_TEXT_STR_ATTR]
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            # Strip instruction qualifier (U+FEFF BOM or its Latin-1 form)
            if val.startswith("\ufeff"):
                val = val[1:]
            if val.startswith("\xef\xbb\xbf"):
                val = val[3:]
            return val
        return None

    @staticmethod
    def _set_text_value(text_tag: QschTag, value: str) -> None:
        """Set the quoted string value on a text tag."""
        while len(text_tag.tokens) <= QSCH_TEXT_STR_ATTR:
            text_tag.tokens.append("0")
        text_tag.tokens[QSCH_TEXT_STR_ATTR] = f'"{value}"'

    # ------------------------------------------------------------------
    # Protocol: read operations
    # ------------------------------------------------------------------

    @property
    def schematic(self) -> QschTag | None:
        """Return the root QschTag tree (for inspection)."""
        return self._root

    @schematic.setter
    def schematic(self, value: QschTag | None) -> None:
        if value is not None:
            self._root = value
            self._index()
            self.updated = True

    def get_components(self, prefixes: str = "*") -> list[str]:
        """Return component references matching *prefixes*."""
        if prefixes == "*":
            return list(self._components.keys())
        result: list[str] = []
        for ref in self._components:
            for prefix in prefixes.split(","):
                prefix = prefix.strip()  # noqa: PLW2901
                if prefix == "*" or ref.upper().startswith(prefix.upper()):
                    result.append(ref)
                    break
        return result

    def get_component(self, reference: str) -> _SchematicComponent:
        """Return one component object by reference."""
        if reference not in self._components:
            raise QSpiceError(f"Component {reference} not found in schematic.")
        comp_tag, symbol_tag = self._components[reference]
        comp = _SchematicComponent(reference)
        comp.position = self._parse_component_position(comp_tag)
        comp.rotation = self._parse_component_rotation(comp_tag)
        comp.attributes = self.get_component_parameters(reference)
        comp.ports = list(self.get_component_nodes(reference))
        # Store raw tags for geometry / symbol-access functions
        comp.attributes["tag"] = comp_tag
        comp.attributes["symbol_tag"] = symbol_tag
        return comp

    def get_component_value(self, element: str) -> str:
        """Return the VALUE text of one component."""
        _comp_tag, symbol_tag = self._components.get(element, (None, None))
        if symbol_tag is None:
            raise QSpiceError(f"Component {element} not found.")
        for text_tag in symbol_tag.items:
            if text_tag.tag != _TAG_TEXT:
                continue
            val = self._get_text_value(text_tag)
            if val and not _REFERENCE_PATTERN.match(val):
                return val
        return ""

    def get_component_parameters(self, element: str) -> dict[str, Any]:
        """Return component-local parameters as a dict."""
        _comp_tag, symbol_tag = self._components.get(element, (None, None))
        if symbol_tag is None:
            raise QSpiceError(f"Component {element} not found.")
        params: dict[str, Any] = {}
        ref_val: str | None = None
        value_val: str | None = None
        for text_tag in symbol_tag.items:
            if text_tag.tag != _TAG_TEXT:
                continue
            val = self._get_text_value(text_tag)
            if val is None:
                continue
            if _REFERENCE_PATTERN.match(val):
                ref_val = val
                continue
            if value_val is None and ref_val is not None:
                value_val = val
                if value_val:
                    params["Value"] = value_val
                continue
            if "=" in val:
                key, _, val_part = val.partition("=")
                params[key.strip()] = val_part.strip()
            elif ref_val is not None and value_val is not None:
                # Additional unnamed parameter
                idx = len([k for k in params if k.startswith("_param")])
                params[f"_param_{idx}"] = val
        return params

    def get_component_nodes(self, reference: str) -> list[str]:
        """Return connected net names for one component."""
        comp_tag, symbol_tag = self._components.get(reference, (None, None))  # noqa: RUF059
        if symbol_tag is None:
            raise QSpiceError(f"Component {reference} not found.")
        nodes: list[str] = []
        for pin_tag in symbol_tag.items:
            if pin_tag.tag != "pin":
                continue
            if len(pin_tag.tokens) > QSCH_SYMBOL_PIN_NET:
                node = pin_tag.tokens[QSCH_SYMBOL_PIN_NET]
                nodes.append(node.strip('"'))
            elif len(pin_tag.tokens) > QSCH_SYMBOL_PIN_NET_BEHAVIORAL:
                node = pin_tag.tokens[QSCH_SYMBOL_PIN_NET_BEHAVIORAL]
                nodes.append(node.strip('"'))
            else:
                nodes.append("")
        return nodes

    def get_component_position(self, reference: str) -> tuple[_Point, int]:
        """Return (position, rotation) for one component."""
        comp_tag, _symbol_tag = self._components.get(reference, (None, None))
        if comp_tag is None:
            raise QSpiceError(f"Component {reference} not found.")
        pos = self._parse_component_position(comp_tag)
        rot = self._parse_component_rotation(comp_tag)
        return pos, rot

    @staticmethod
    def _parse_component_position(comp_tag: QschTag) -> _Point:
        if len(comp_tag.tokens) > QSCH_COMPONENT_POS:
            raw = comp_tag.tokens[QSCH_COMPONENT_POS]
            if raw.startswith("(") and raw.endswith(")"):
                inner = raw[1:-1]
                parts = inner.split(",")
                if len(parts) == 2:  # noqa: PLR2004
                    return _Point(int(parts[0]), int(parts[1]))
        return _Point(0, 0)

    @staticmethod
    def _parse_component_rotation(comp_tag: QschTag) -> int:
        if len(comp_tag.tokens) > QSCH_COMPONENT_ROTATION:
            return int(comp_tag.tokens[QSCH_COMPONENT_ROTATION])
        return 0

    # ------------------------------------------------------------------
    # Protocol: write operations
    # ------------------------------------------------------------------

    def add_component(self, component: _SchematicComponent, **kwargs: Any) -> None:
        """Append one component to the schematic.

        Uses the raw ``QschTag`` stored in ``component.attributes['tag']``
        when available (from ``schematic_editor_edits``), falling back
        to a minimal tag for simple programmatic use.
        """
        raw_tag = component.attributes.get("tag")
        if raw_tag is not None and isinstance(raw_tag, QschTag):
            comp_tag = raw_tag
        else:
            comp_tag = QschTag(
                _TAG_COMPONENT,
                f"({component.position.X},{component.position.Y})",
                str(component.rotation),
                "0",
            )
            sym_tag = QschTag(_TAG_SYMBOL, "unknown")
            ref_text = QschTag(_TAG_TEXT, *(["0"] * QSCH_TEXT_STR_ATTR), f'"{component.reference}"')
            sym_tag.items.append(ref_text)
            comp_tag.items.append(sym_tag)
        self._root.items.append(comp_tag)
        self._index()
        self.updated = True

    def remove_component(self, reference: str) -> None:
        """Remove one component and its symbol from the schematic."""
        if reference not in self._components:
            raise QSpiceError(f"Component {reference} not found.")
        comp_tag, _symbol_tag = self._components.pop(reference)
        self._root.items.remove(comp_tag)
        self.updated = True

    def set_component_value(self, reference: str, value: object) -> None:
        """Update the VALUE text of one component."""
        _comp_tag, symbol_tag = self._components.get(reference, (None, None))
        if symbol_tag is None:
            raise QSpiceError(f"Component {reference} not found.")
        ref_found = False
        for text_tag in symbol_tag.items:
            if text_tag.tag != _TAG_TEXT:
                continue
            val = self._get_text_value(text_tag)
            if val and _REFERENCE_PATTERN.match(val):
                ref_found = True
                continue
            if ref_found:
                self._set_text_value(text_tag, str(value))
                self.updated = True
                return
        self.updated = True

    def set_component_position(
        self,
        reference: str,
        position: Any,
        rotation: Any,
        mirror: bool = False,
    ) -> None:
        """Update one component's placement."""
        comp_tag, _symbol_tag = self._components.get(reference, (None, None))
        if comp_tag is None:
            raise QSpiceError(f"Component {reference} not found.")
        x = position.X if hasattr(position, "X") else position[0]
        y = position.Y if hasattr(position, "Y") else position[1]
        rot = int(rotation)
        if mirror:
            rot += 8  # QSPICE mirror bit
        if len(comp_tag.tokens) > QSCH_COMPONENT_POS:
            comp_tag.tokens[QSCH_COMPONENT_POS] = f"({x},{y})"
        if len(comp_tag.tokens) > QSCH_COMPONENT_ROTATION:
            comp_tag.tokens[QSCH_COMPONENT_ROTATION] = str(rot)
        self.updated = True

    def set_component_parameters(self, element: str, **kwargs: Any) -> None:
        """Update parameters on one component."""
        _comp_tag, symbol_tag = self._components.get(element, (None, None))
        if symbol_tag is None:
            raise QSpiceError(f"Component {element} not found.")
        for key, val in kwargs.items():
            if key == "Value":
                self.set_component_value(element, val)
                continue
            # Update or add parameter text line
            param_str = f"{key}={val}"
            found = False
            for text_tag in symbol_tag.items:
                if text_tag.tag != _TAG_TEXT:
                    continue
                existing = self._get_text_value(text_tag)
                if existing and existing.startswith(f"{key}="):
                    self._set_text_value(text_tag, param_str)
                    found = True
                    break
            if not found:
                new_text = QschTag(
                    _TAG_TEXT,
                    *(["0"] * QSCH_TEXT_STR_ATTR),
                    f'"{param_str}"',
                )
                symbol_tag.items.append(new_text)
        self.updated = True

    def set_element_model(self, device: str, model: str) -> None:
        """Update the model of one component."""
        _comp_tag, symbol_tag = self._components.get(device, (None, None))
        if symbol_tag is None:
            raise QSpiceError(f"Component {device} not found.")
        # Model is typically the VALUE text for transistors etc.
        ref_found = False
        for text_tag in symbol_tag.items:
            if text_tag.tag != _TAG_TEXT:
                continue
            val = self._get_text_value(text_tag)
            if val and _REFERENCE_PATTERN.match(val):
                ref_found = True
                continue
            if ref_found:
                self._set_text_value(text_tag, model)
                self.updated = True
                return
        self.updated = True

    def set_parameter(self, param: str, value: object) -> None:
        """Set a schematic-level .param directive."""
        param_str = f".param {param}={value}"
        # Check if we already have this param
        for text_tag, _idx in self._instructions:
            val = self._get_text_value(text_tag)
            if val and val.startswith(f".param {param}="):
                self._set_text_value(text_tag, param_str)
                self.updated = True
                return
        # Add as new instruction
        self.add_instruction(param_str)

    def add_instruction(self, instruction: str) -> None:
        """Add one SPICE directive line to the schematic."""
        instr = instruction
        if instr.startswith(QSCH_TEXT_INSTR_QUALIFIER):
            instr = instr[1:]
        # Build a text tag: «text (x,y) size rot comment color -1 -1 "instr"»
        x = 400
        y = -40 - (len(self._instructions) * 80)
        # Store directives as plain Latin-1 text. Do not prefix with the UTF-8 BOM
        # qualifier: QSPICE .qsch files are Latin-1, and mixing a BOM with
        # Latin-1 unit suffixes (for example 300µ) makes QSPICE show U+FFFD.
        text_tag = QschTag(
            _TAG_TEXT,
            f"({x},{y})",
            "1",  # size
            "0",  # rotation
            "0",  # comment flag
            "0x1000000",  # color
            "-1",
            "-1",
            f'"{instr}"',
        )
        self._root.items.append(text_tag)
        self._instructions.append((text_tag, len(self._instructions)))
        self.updated = True

    def remove_instruction(self, instruction: str) -> bool:
        """Remove one matching directive exactly. Returns True if removed."""
        norm = instruction.strip()
        if norm.startswith(QSCH_TEXT_INSTR_QUALIFIER):
            norm = norm[1:]
        for text_tag, idx in list(self._instructions):
            val = self._get_text_value(text_tag)
            if val:
                val_clean = val
                if val_clean.startswith(QSCH_TEXT_INSTR_QUALIFIER):
                    val_clean = val_clean[1:]
                if val_clean.strip() == norm:
                    self._root.items.remove(text_tag)
                    self._instructions.remove((text_tag, idx))
                    self.updated = True
                    return True
        return False

    def remove_Xinstruction(self, search_pattern: str) -> bool:  # noqa: N802
        """Remove directives matching a regular expression. Returns True if any removed."""
        pat = re.compile(search_pattern) if isinstance(search_pattern, str) else search_pattern
        removed = False
        for text_tag, idx in list(self._instructions):
            val = self._get_text_value(text_tag)
            if val is None:
                continue
            val_clean = val
            if val_clean.startswith(QSCH_TEXT_INSTR_QUALIFIER):
                val_clean = val_clean[1:]
            if pat.search(val_clean):
                self._root.items.remove(text_tag)
                self._instructions.remove((text_tag, idx))
                self.updated = True
                removed = True
        return removed

    def get_subcircuit(self, reference: str) -> QschEditor:
        """Return a new editor for one external subcircuit definition."""
        from pathlib import Path as _Path  # noqa: PLC0415

        from qspice_mcp.services.subcircuit._clean_room import (  # noqa: PLC0415
            resolve_supported_subcircuit_definition_path,
        )

        if reference not in self._components:
            raise QSpiceError(f"Component {reference} not found in schematic.")
        if not reference.upper().startswith("X"):
            raise QSpiceError(f"Component {reference} is not a subcircuit instance.")
        definition_name = self.get_component_value(reference).strip()
        if not definition_name:
            raise QSpiceError(
                f"Subcircuit instance {reference} has no definition name in the schematic."
            )
        parent_path = _Path(self._path).resolve(strict=False)
        definition_path = resolve_supported_subcircuit_definition_path(
            parent_path,
            workspace_root=self._workspace_root,
            definition_name=definition_name,
        )
        return QschEditor(
            str(definition_path),
            workspace_root=self._workspace_root,
        )

    def save_as(self, qsch_filename: str | Path) -> None:
        """Persist the schematic tree to a .qsch file."""
        from pathlib import Path as _Path  # noqa: PLC0415

        path = _Path(qsch_filename)
        out = self._root.out(level=0)
        # The instruction qualifier \ufeff cannot be encoded in Latin-1.
        # Replace it with the UTF-8 BOM byte sequence that QSPICE expects.
        out = out.replace("\ufeff", "\xef\xbb\xbf")
        data = _QSCH_BINARY_PREFIX + out.encode("latin-1")
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f"{path.name}.tmp")
        last_error: OSError | None = None
        for _attempt in range(3):
            try:
                temp_path.write_bytes(data)
                temp_path.replace(path)
            except OSError as exc:
                last_error = exc
                temp_path.unlink(missing_ok=True)
            else:
                self.updated = False
                return
        if last_error is not None:
            raise last_error

    def save_netlist(self, path: str) -> None:
        """Generate and write a SPICE netlist from the schematic.

        Delegates to the clean-room netlist renderer using the original
        file path, since ``save_netlist`` is always called before any
        in-memory edits are applied.
        """
        from pathlib import Path as _Path  # noqa: PLC0415

        from qspice_mcp.services.simulation._clean_room_netlist import (  # noqa: PLC0415
            render_clean_room_netlist,
        )

        destination = _Path(path)
        result = render_clean_room_netlist(_Path(self._path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result.netlist_text, encoding="utf-8")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        n_comps = len(self._components)
        n_instrs = len(self._instructions)
        return f"QschEditor(path={self._path!r}, components={n_comps}, instructions={n_instrs})"
