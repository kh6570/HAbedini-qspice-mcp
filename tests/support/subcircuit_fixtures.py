"""Shared subcircuit ``.qsch`` byte fixtures used across unit tests.

Kept in a non-``test_*`` module so multiple test modules can reuse the same
synthesized schematic bytes without importing one test module from another.
"""

from __future__ import annotations


def supported_subcircuit_schematic_bytes(
    *,
    reference: str = "X1",
    definition_name: str = "COMPARATOR",
    description: str = "Comparator",
) -> bytes:
    """Return a top-level schematic that instantiates one external subcircuit."""
    return b"".join(
        (
            b"\xff\xd8\xff\xdb",
            b"\xabschematic\r\n",
            b"  \xabcomponent (400,400) 0 0\r\n",
            b"    \xabsymbol X\r\n",
            b"      \xabtype: X\xbb\r\n",
            f"      \xabdescription: {description}\xbb\r\n".encode("latin-1"),
            f'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "{reference}"\xbb\r\n'.encode(
                "latin-1"
            ),
            f'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "{definition_name}"\xbb\r\n'.encode(
                "latin-1"
            ),
            b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "INP"\xbb\r\n',
            b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "OUT"\xbb\r\n',
            b"    \xbb\r\n",
            b"  \xbb\r\n",
            b"\xbb\r\n\r\n",
        )
    )


def supported_leaf_subcircuit_definition_bytes() -> bytes:
    """Return a leaf subcircuit definition schematic with an R and a C."""
    return (
        b"\xff\xd8\xff\xdb"
        b"\xabschematic\r\n"
        b"  \xabcomponent (400,400) 0 0\r\n"
        b"    \xabsymbol R\r\n"
        b"      \xabtype: R\xbb\r\n"
        b"      \xabdescription: Feedback\xbb\r\n"
        b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n'
        b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "2k"\xbb\r\n'
        b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "1"\xbb\r\n'
        b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "2"\xbb\r\n'
        b"    \xbb\r\n"
        b"  \xbb\r\n"
        b"  \xabcomponent (800,400) 0 0\r\n"
        b"    \xabsymbol C\r\n"
        b"      \xabtype: C\xbb\r\n"
        b"      \xabdescription: Comp\xbb\r\n"
        b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "C1"\xbb\r\n'
        b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "10p"\xbb\r\n'
        b'      \xabpin (0,200) (0,0) 1 0 0 0x0 -1 "1"\xbb\r\n'
        b'      \xabpin (0,-200) (0,0) 1 0 0 0x0 -1 "2"\xbb\r\n'
        b"    \xbb\r\n"
        b"  \xbb\r\n"
        b"\xbb\r\n\r\n"
    )


__all__ = [
    "supported_leaf_subcircuit_definition_bytes",
    "supported_subcircuit_schematic_bytes",
]
