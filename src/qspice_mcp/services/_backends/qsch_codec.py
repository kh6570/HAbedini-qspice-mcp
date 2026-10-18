"""Latin-1 codec for QSpice `.qsch` and `.qsym` files."""

from __future__ import annotations


def decode_qsch_bytes(raw_bytes: bytes) -> str:
    """Decode schematic bytes using QSpice's Latin-1 wire format.

    QSpice `.qsch` files are Latin-1, with guillemets as single bytes
    ``\\xab``/``\\xbb``. Inline UTF-8 BOM byte sequences may appear before
    analysis directives; strip those qualifiers before decoding. Do not
    attempt whole-file UTF-8 decoding: valid UTF-8 byte runs can mis-decode
    Latin-1 guillemets.
    """

    stripped = raw_bytes.replace(b"\xef\xbb\xbf", b"")
    return stripped.decode("latin-1")


__all__ = ["decode_qsch_bytes"]
