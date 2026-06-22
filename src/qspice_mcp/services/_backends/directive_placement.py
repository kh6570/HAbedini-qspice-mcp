"""Placement helpers for top-level schematic analysis directive text."""

from __future__ import annotations

_DEFAULT_DIRECTIVE_X = 100
_DEFAULT_DIRECTIVE_Y = -40
_DIRECTIVE_Y_BELOW_MARGIN = 360
_DIRECTIVE_Y_STEP = 80


def compute_directive_position(
    component_anchors: tuple[tuple[int, int], ...],
    directive_index: int,
) -> tuple[int, int]:
    """Return a sheet position for one analysis directive text item.

    When components exist, directives are stacked below the lowest placed part so
    they do not overlap symbol value strings (for example long ``PULSE(...)`` on
    voltage sources). Empty schematics keep the legacy top-left fallback.
    """

    if directive_index < 0:
        raise ValueError("directive_index must be non-negative.")
    if not component_anchors:
        return (
            _DEFAULT_DIRECTIVE_X,
            _DEFAULT_DIRECTIVE_Y - directive_index * _DIRECTIVE_Y_STEP,
        )
    min_x = min(x for x, _ in component_anchors)
    max_y = max(y for _, y in component_anchors)
    return (
        min_x,
        max_y + _DIRECTIVE_Y_BELOW_MARGIN + directive_index * _DIRECTIVE_Y_STEP,
    )


__all__ = ["compute_directive_position"]
