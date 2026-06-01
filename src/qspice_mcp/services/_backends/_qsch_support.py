"""Repo-owned QSCH tag parser and constants.

Provides the minimal QschTag implementation and QSCH format constants that
are defined locally for QSCH tag construction.  This module
is self-contained and does not import any third-party schematic packages.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# QSCH format constants (stable indices defined by the QSPICE file format)
# ---------------------------------------------------------------------------

QSCH_SYMBOL_TEXT_REFDES: int = 0
QSCH_SYMBOL_TEXT_VALUE: int = 1
QSCH_TEXT_STR_ATTR: int = 8
QSCH_TEXT_POS: int = 1
QSCH_TEXT_SIZE: int = 2
QSCH_TEXT_ROTATION: int = 3
QSCH_TEXT_COMMENT: int = 4
QSCH_TEXT_COLOR: int = 5
QSCH_TEXT_INSTR_QUALIFIER: str = "\ufeff"
QSCH_COMPONENT_POS: int = 1
QSCH_COMPONENT_ROTATION: int = 2
QSCH_SYMBOL_PIN_NET: int = 8
QSCH_SYMBOL_PIN_POS1: int = 1
QSCH_SYMBOL_PIN_POS2: int = 2
QSCH_SYMBOL_PIN_NET_BEHAVIORAL: int = 9

_QSCH_TAG_OPEN: str = "\xab"
_QSCH_TAG_CLOSE: str = "\xbb"
_QSCH_TAG_SELF_CLOSE: str = "\xab\xbb"

_POINT_COORD_COUNT = 2
_MIN_QUOTED_LEN = 2


class QschTag:
    """A single node in a QSPICE schematic XML-like tag tree.

    Models the ``«tag attr1 attr2 ...»`` / ``«/tag»`` format used by QSPICE
    ``.qsch`` files.  Provides attribute access by positional index and
    child-item filtering by label.
    """

    __slots__ = ("items", "tag", "tokens")

    def __init__(self, tag: str, *tokens: str) -> None:
        self.tag = tag
        self.tokens: list[str] = [tag]
        self.tokens.extend(str(t) for t in tokens)
        self.items: list[QschTag] = []

    # -- attribute access --

    def get_attr(self, index: int) -> str | int | float | tuple[int, int]:  # noqa: PLR0911
        """Return the token at *index*.

        - ``(x,y)`` position tokens → ``(int, int)`` tuple
        - Quoted strings ``"value"`` → ``"value"`` (one layer stripped)
        - Integer-like tokens → ``int``
        - Other tokens → ``str`` as-is
        """
        value = self.tokens[index]
        if isinstance(value, (int, float)):
            return value
        # Parse (x,y) position tokens → tuple
        if value.startswith("(") and value.endswith(")"):
            inner = value[1:-1]
            parts = inner.split(",")
            if len(parts) == _POINT_COORD_COUNT:
                try:
                    return (int(parts[0]), int(parts[1]))
                except ValueError:
                    pass
        # Strip one layer of QSCH double-quote wrapping: "value" → value
        if len(value) >= _MIN_QUOTED_LEN and value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        # Parse numeric tokens (int or float)
        if value.startswith("0x"):
            return value  # hex values stay as strings
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def set_attr(self, index: int, value: str | int | tuple[int, int]) -> None:
        """Set the token at *index*.

        Strings are wrapped in double quotes (``"value"``) to match QSCH
        format.  Tuples are formatted as ``(x,y)``.
        """
        if isinstance(value, tuple):
            value_str = f"({value[0]},{value[1]})"
        elif isinstance(value, int):
            value_str = str(value)
        elif isinstance(value, str) and not (
            value.startswith('"') or value.startswith("(") or value.startswith("0x")
        ):
            value_str = f'"{value}"'
        else:
            value_str = value
        self.tokens[index] = value_str

    # -- child items --

    def get_items(self, label: str) -> list[QschTag]:
        """Return child tags whose ``tag`` matches *label*."""
        return [item for item in self.items if item.tag == label]

    def get_text(self, label: str) -> str | None:
        """Return the first child text item's string attribute."""
        for item in self.items:
            if item.tag == label and len(item.tokens) > QSCH_TEXT_STR_ATTR:
                return item.tokens[QSCH_TEXT_STR_ATTR]
        return None

    # -- serialization --

    def out(self, level: int = 0) -> str:
        """Serialize this tag and its children to QSCH wire format.

        QSPICE ``.qsch`` tags use a compact indented format:
        - Leaf tags: ``«tag attr1 attr2»``  (self-closing, single line)
        - Parent tags: ``«tag attr1 attr2\\n  ...children...\\n  »``
          where the closing marker is just ``»`` at child indentation.
        """
        indent = " " * level
        tokens = [str(t) for t in self.tokens]
        tokens[0] = _QSCH_TAG_OPEN + self.tag
        if not self.items:
            return indent + " ".join(tokens) + _QSCH_TAG_CLOSE + "\n"
        child_indent = indent + "  "
        line = indent + " ".join(tokens) + "\n"
        for child in self.items:
            line += child.out(level + 1)
        line += child_indent + _QSCH_TAG_CLOSE + "\n"
        return line

    # -- parsing (class method) --

    @classmethod
    def parse(cls, stream: str, start: int) -> tuple[QschTag, int]:
        """Parse one ``«...»`` tag from *stream* starting at *start*.

        Returns ``(tag, consumed)`` where *consumed* is the number of
        characters read.
        """
        assert stream[start] == _QSCH_TAG_OPEN, f"Expected '{_QSCH_TAG_OPEN}' at position {start}"
        end = stream.find(_QSCH_TAG_CLOSE, start)
        if end == -1:
            raise ValueError(f"Unterminated tag starting at position {start}")
        inner = stream[start + 1 : end]
        tokens = inner.split()
        if not tokens:
            raise ValueError(f"Empty tag at position {start}")
        tag = QschTag(tokens[0], *tokens[1:])
        return tag, end + 1 - start

    def __repr__(self) -> str:
        return f"QschTag({self.tag!r}, tokens={len(self.tokens)})"


__all__ = [
    "QSCH_COMPONENT_POS",
    "QSCH_COMPONENT_ROTATION",
    "QSCH_SYMBOL_PIN_NET",
    "QSCH_SYMBOL_PIN_NET_BEHAVIORAL",
    "QSCH_SYMBOL_PIN_POS1",
    "QSCH_SYMBOL_PIN_POS2",
    "QSCH_SYMBOL_TEXT_REFDES",
    "QSCH_SYMBOL_TEXT_VALUE",
    "QSCH_TEXT_COLOR",
    "QSCH_TEXT_COMMENT",
    "QSCH_TEXT_INSTR_QUALIFIER",
    "QSCH_TEXT_POS",
    "QSCH_TEXT_ROTATION",
    "QSCH_TEXT_SIZE",
    "QSCH_TEXT_STR_ATTR",
    "QschTag",
]
