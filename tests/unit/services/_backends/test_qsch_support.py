"""Tests for repo-owned QschTag and QSCH format constants."""

from __future__ import annotations

import pytest

from qspice_mcp.services._backends._qsch_support import (
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
    QschTag,
)

# QSPICE guillemet delimiters used by parse/out
_QSCH_OPEN = "\u00ab"
_QSCH_CLOSE = "\u00bb"


# ---------------------------------------------------------------------------
# QSCH constants
# ---------------------------------------------------------------------------


def test_qsch_constants_are_stable() -> None:
    """All exported QSCH constants exist and have expected types."""
    assert QSCH_SYMBOL_TEXT_REFDES == 0
    assert QSCH_SYMBOL_TEXT_VALUE == 1
    assert QSCH_TEXT_STR_ATTR == 8
    assert QSCH_TEXT_POS == 1
    assert QSCH_TEXT_SIZE == 2
    assert QSCH_TEXT_ROTATION == 3
    assert QSCH_TEXT_COMMENT == 4
    assert QSCH_TEXT_COLOR == 5
    assert QSCH_TEXT_INSTR_QUALIFIER == "\ufeff"
    assert QSCH_COMPONENT_POS == 1
    assert QSCH_COMPONENT_ROTATION == 2
    assert QSCH_SYMBOL_PIN_NET == 8
    assert QSCH_SYMBOL_PIN_POS1 == 1
    assert QSCH_SYMBOL_PIN_POS2 == 2
    assert QSCH_SYMBOL_PIN_NET_BEHAVIORAL == 9


# ---------------------------------------------------------------------------
# QschTag construction
# ---------------------------------------------------------------------------


def test_qsch_tag_creation_basic() -> None:
    tag = QschTag("Symbol")
    assert tag.tag == "Symbol"
    assert tag.tokens == ["Symbol"]
    assert tag.items == []


def test_qsch_tag_creation_with_tokens() -> None:
    tag = QschTag("Attr", "1", "2", "3")
    assert tag.tag == "Attr"
    assert tag.tokens == ["Attr", "1", "2", "3"]


# ---------------------------------------------------------------------------
# get_attr — type coercion (index 1 = first attr token after tag name)
# ---------------------------------------------------------------------------


def test_get_attr_integer() -> None:
    tag = QschTag("X", "42")
    assert tag.get_attr(1) == 42


def test_get_attr_float() -> None:
    tag = QschTag("X", "0.5")
    assert tag.get_attr(1) == 0.5


def test_get_attr_string_quoted() -> None:
    tag = QschTag("X", '"hello"')
    assert tag.get_attr(1) == "hello"


def test_get_attr_string_unquoted() -> None:
    tag = QschTag("X", "unquoted")
    assert tag.get_attr(1) == "unquoted"


def test_get_attr_position_tuple() -> None:
    tag = QschTag("X", "(10,-20)")
    assert tag.get_attr(1) == (10, -20)


def test_get_attr_hex_string_stays_string() -> None:
    tag = QschTag("X", "0x1A")
    result = tag.get_attr(1)
    assert result == "0x1A"
    assert isinstance(result, str)


def test_get_attr_tag_token_returns_tag_name() -> None:
    """The tag name itself (index 0) is returned as a string."""
    tag = QschTag("Symbol")
    assert tag.get_attr(0) == "Symbol"


def test_get_attr_position_tuple_too_many_parts_falls_through() -> None:
    """A 'position' string with != 2 parts is returned as a plain string."""
    tag = QschTag("X", "(1,2,3)")
    assert tag.get_attr(1) == "(1,2,3)"


def test_get_attr_position_tuple_non_integer_parts_falls_through() -> None:
    """A position string with non-integer parts triggers ValueError fallthrough."""
    tag = QschTag("X", "(a,b)")
    assert tag.get_attr(1) == "(a,b)"


def test_get_attr_float_scientific_notation() -> None:
    """Floats in scientific notation are parsed correctly."""
    tag = QschTag("X", "3.14e-5")
    assert tag.get_attr(1) == pytest.approx(3.14e-5)


def test_get_attr_float_with_fraction() -> None:
    """Float with fractional part (non-integer) is parsed as float."""
    tag = QschTag("X", "0.125")
    assert tag.get_attr(1) == pytest.approx(0.125)


# ---------------------------------------------------------------------------
# set_attr
# ---------------------------------------------------------------------------


def test_set_attr_int() -> None:
    tag = QschTag("X", "old")
    tag.set_attr(1, 42)
    assert tag.tokens[1] == "42"


def test_set_attr_tuple() -> None:
    tag = QschTag("X", "old")
    tag.set_attr(1, (30, 40))
    assert tag.tokens[1] == "(30,40)"


def test_set_attr_string_wrapping() -> None:
    tag = QschTag("X", "old")
    tag.set_attr(1, "newname")
    assert tag.tokens[1] == '"newname"'


def test_set_attr_string_already_quoted() -> None:
    tag = QschTag("X", "old")
    tag.set_attr(1, '"already"')
    assert tag.tokens[1] == '"already"'


def test_set_attr_string_already_paren() -> None:
    """Strings already starting with '(' are not re-wrapped."""
    tag = QschTag("X", "old")
    tag.set_attr(1, "(5,5)")
    assert tag.tokens[1] == "(5,5)"


def test_set_attr_string_hex() -> None:
    """hex-like strings are not re-wrapped."""
    tag = QschTag("X", "old")
    tag.set_attr(1, "0xFF")
    assert tag.tokens[1] == "0xFF"


# ---------------------------------------------------------------------------
# get_items
# ---------------------------------------------------------------------------


def test_get_items_empty() -> None:
    tag = QschTag("Root")
    assert tag.get_items("Child") == []


def test_get_items_filters_by_label() -> None:
    parent = QschTag("Root")
    parent.items = [QschTag("A"), QschTag("B"), QschTag("A")]
    a_children = parent.get_items("A")
    assert len(a_children) == 2
    assert all(c.tag == "A" for c in a_children)


def test_get_items_no_match() -> None:
    parent = QschTag("Root")
    parent.items = [QschTag("A")]
    assert parent.get_items("B") == []


# ---------------------------------------------------------------------------
# get_text
# ---------------------------------------------------------------------------


def test_get_text_returns_8th_attribute() -> None:
    parent = QschTag("Symbol")
    # QSCH_TEXT_STR_ATTR = 8, so we need 9 tokens (tag + 8 attrs), value at index 8
    text_tag = QschTag("Text", *(["0"] * 7), '"label"')
    parent.items = [text_tag]
    assert parent.get_text("Text") == '"label"'


def test_get_text_no_match() -> None:
    parent = QschTag("Symbol")
    parent.items = [QschTag("Other")]
    assert parent.get_text("Text") is None


def test_get_text_insufficient_tokens() -> None:
    parent = QschTag("Symbol")
    text_tag = QschTag("Text", "only_few")
    parent.items = [text_tag]
    # tokens shorter than QSCH_TEXT_STR_ATTR+1 -> None
    assert parent.get_text("Text") is None


# ---------------------------------------------------------------------------
# out - serialization
# ---------------------------------------------------------------------------


def test_out_leaf_tag() -> None:
    tag = QschTag("Attr", "1", "2")
    result = tag.out(level=0)
    assert result == f"{_QSCH_OPEN}Attr 1 2{_QSCH_CLOSE}\n"


def test_out_parent_tag_with_children() -> None:
    parent = QschTag("Root", "p1")
    child = QschTag("Child", "c1")
    parent.items = [child]
    result = parent.out(level=0)
    # out() uses 1-space-per-level; child at level 1 gets 1 space
    expected = f"{_QSCH_OPEN}Root p1\n {_QSCH_OPEN}Child c1{_QSCH_CLOSE}\n  {_QSCH_CLOSE}\n"
    assert result == expected


def test_out_nested_levels() -> None:
    root = QschTag("A")
    mid = QschTag("B")
    leaf = QschTag("C")
    mid.items = [leaf]
    root.items = [mid]
    result = root.out(level=0)
    # out() uses 1-space-per-level, child_indent = indent + 2 spaces
    expected = (
        f"{_QSCH_OPEN}A\n"
        f" {_QSCH_OPEN}B\n"
        f"  {_QSCH_OPEN}C{_QSCH_CLOSE}\n"
        f"   {_QSCH_CLOSE}\n"
        f"  {_QSCH_CLOSE}\n"
    )
    assert result == expected


def test_out_respects_indent_level() -> None:
    tag = QschTag("X", "v")
    result = tag.out(level=2)
    assert result.startswith("  \u00ab")  # 2 spaces for level=2


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


def test_parse_simple_leaf() -> None:
    stream = f"{_QSCH_OPEN}Symbol name{_QSCH_CLOSE}"
    tag, consumed = QschTag.parse(stream, 0)
    assert tag.tag == "Symbol"
    assert tag.tokens == ["Symbol", "name"]
    assert consumed == len(stream)


def test_parse_with_position() -> None:
    stream = f"{_QSCH_OPEN}Attr (10,20){_QSCH_CLOSE}extra"
    tag, consumed = QschTag.parse(stream, 0)
    assert tag.tag == "Attr"
    assert tag.tokens[1] == "(10,20)"
    assert consumed == len(f"{_QSCH_OPEN}Attr (10,20){_QSCH_CLOSE}")


def test_parse_raises_on_unterminated() -> None:
    stream = f"{_QSCH_OPEN}incomplete"
    with pytest.raises(ValueError, match="Unterminated"):
        QschTag.parse(stream, 0)


def test_parse_raises_on_empty() -> None:
    stream = f"{_QSCH_OPEN}{_QSCH_CLOSE}"
    with pytest.raises(ValueError, match="Empty"):
        QschTag.parse(stream, 0)


def test_parse_middle_of_stream() -> None:
    """parse() at start pointing to second tag in a multi-tag stream."""
    stream = f"{_QSCH_OPEN}A a{_QSCH_CLOSE}{_QSCH_OPEN}B b{_QSCH_CLOSE}"
    offset = len(f"{_QSCH_OPEN}A a{_QSCH_CLOSE}")  # = 5
    tag, consumed = QschTag.parse(stream, offset)
    assert tag.tag == "B"
    assert consumed == 5


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------


def test_repr() -> None:
    tag = QschTag("Symbol", "a", "b")
    r = repr(tag)
    assert "QschTag" in r
    assert "Symbol" in r
    assert "tokens=3" in r


# ---------------------------------------------------------------------------
# Integration-style round-trips
# ---------------------------------------------------------------------------


def test_round_trip_leaf() -> None:
    """Parse a flat leaf tag and re-serialize it."""
    original = f'{_QSCH_OPEN}Symbol (0,0) "REFDES"{_QSCH_CLOSE}'
    tag, _ = QschTag.parse(original, 0)
    regenerated = tag.out(level=0).strip()
    assert regenerated == original


def test_out_is_parseable_leaf() -> None:
    """The output of a leaf tag can be parsed back to an equivalent tag."""
    tag = QschTag("X", "42", '"hello"')
    out = tag.out(level=0)
    parsed, _ = QschTag.parse(out, 0)
    assert parsed.tag == tag.tag
    assert parsed.tokens == tag.tokens


def test_out_is_parseable_parent() -> None:
    """The output of a parent tag can be parsed; children come as text after."""
    root = QschTag("Root", "p1")
    child = QschTag("Child", "c1")
    root.items = [child]
    out = root.out(level=0)
    # parse() parses ONE tag from the stream; since out() puts tag+attrs on
    # the first line, and the child tag on the second line starts with '«',
    # parse will slurp the opening «Root p1» plus the child «Child c1»
    # as part of the token block (space-delimited).  This is expected.
    parsed, _consumed = QschTag.parse(out, 0)
    assert parsed.tag == "Root"
    # The first V got merged during tokenisation; just verify the outer tag
    assert parsed.tokens[0] == "Root"
    assert parsed.tokens[1] == "p1"
