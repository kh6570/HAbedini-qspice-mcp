"""Shared helpers for resolving step selections from step metadata."""

from __future__ import annotations

from math import isclose
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class _StepVariable(Protocol):
    """Minimal protocol for one parsed sweep variable."""

    @property
    def name(self) -> object: ...

    @property
    def values(self) -> Sequence[object]: ...


StepFilterValue = str | int | float


def _coerce_step_filter_value(value: object) -> StepFilterValue:
    """Normalize one user-supplied or parsed step value."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        return value
    return str(value)


def normalize_step_filters(step_filters: Mapping[str, object] | None) -> dict[str, StepFilterValue]:
    """Normalize one step filter mapping for case-insensitive matching."""

    if not step_filters:
        return {}
    return {
        str(key).strip().lower(): _coerce_step_filter_value(value)
        for key, value in step_filters.items()
    }


def _values_match(expected: StepFilterValue, actual: StepFilterValue) -> bool:
    """Return whether two step values should be treated as equal."""

    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return isclose(float(expected), float(actual), rel_tol=0.0, abs_tol=1e-12)
    return str(expected).strip().lower() == str(actual).strip().lower()


def build_step_value_maps(
    step_variables: Sequence[_StepVariable],
    step_count: int,
) -> tuple[dict[str, StepFilterValue], ...]:
    """Render one per-step mapping from a sequence of step variables."""

    rendered_steps: list[dict[str, StepFilterValue]] = []
    for index in range(step_count):
        values: dict[str, StepFilterValue] = {}
        for variable in step_variables:
            name = str(variable.name).strip().lower()
            variable_values = tuple(variable.values)
            if index < len(variable_values):
                values[name] = _coerce_step_filter_value(variable_values[index])
        rendered_steps.append(values)
    return tuple(rendered_steps)


def resolve_step_selection(
    step_variables: Sequence[_StepVariable],
    step_count: int,
    *,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    default_step: int = 0,
) -> int:
    """Resolve one requested step index from an explicit index or filter set."""

    if step_count < 1:
        raise ValueError("No simulation steps are available for this artifact.")

    if step is not None and not 0 <= step < step_count:
        raise ValueError(f"Step index {step} is not available. Valid range: 0..{step_count - 1}")

    normalized_filters = normalize_step_filters(step_filters)
    if not normalized_filters:
        return default_step if step is None else step

    if not step_variables:
        raise ValueError(
            "step_filters require step metadata, but no step variables were "
            "found for this artifact."
        )

    step_values = build_step_value_maps(step_variables, step_count)
    matches = [
        index
        for index, values in enumerate(step_values)
        if all(
            key in values and _values_match(expected, values[key])
            for key, expected in normalized_filters.items()
        )
    ]
    if not matches:
        raise ValueError(
            f"No simulation step matched the requested step_filters: {dict(normalized_filters)}"
        )
    if len(matches) > 1:
        raise ValueError(
            "step_filters resolved to multiple simulation steps; provide an explicit step index."
        )

    resolved_step = matches[0]
    if step is not None and step != resolved_step:
        raise ValueError("step and step_filters resolve to different simulation steps.")
    return resolved_step


__all__ = [
    "StepFilterValue",
    "build_step_value_maps",
    "normalize_step_filters",
    "resolve_step_selection",
]
