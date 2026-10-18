"""Lazy matplotlib import so service-module import stays cheap."""

from __future__ import annotations

from typing import Any


def pyplot() -> Any:
    """Return pyplot after selecting the non-interactive backend.

    Imported inside the function on purpose: importing matplotlib at module
    scope adds about a second to server startup for tools that never plot.
    """

    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt  # noqa: PLC0415

    return plt
