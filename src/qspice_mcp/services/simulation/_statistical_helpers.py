"""Shared helpers for statistical prepare/run services."""

from __future__ import annotations

from re import fullmatch
from typing import TYPE_CHECKING, TypeVar

from qspice_mcp.services._backends.schematic_editor import open_schematic_editor

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol

_TargetT = TypeVar("_TargetT")
_SPICE_NUMBER_PATTERN = r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([A-Za-zµ]*)"
_SPICE_SUFFIX_FACTORS: tuple[tuple[str, float], ...] = (
    ("meg", 1_000_000.0),
    ("mil", 25.4e-6),
    ("t", 1_000_000_000_000.0),
    ("g", 1_000_000_000.0),
    ("k", 1_000.0),
    ("m", 0.001),
    ("u", 1e-6),
    ("µ", 1e-6),
    ("n", 1e-9),
    ("p", 1e-12),
    ("f", 1e-15),
)


def _format_expression_number(value: float) -> str:
    """Render one float compactly for QSPICE expression text."""

    return format(value, ".15g")


def _resolve_target_nominal(
    name: str,
    spec: Mapping[str, int | float],
    *,
    target_label: str,
    nominal_resolver: Callable[[str], float] | None,
) -> float:
    if "nominal" in spec:
        return float(spec["nominal"])
    if nominal_resolver is not None:
        return nominal_resolver(name)
    raise ValueError(f"{target_label} {name!r} must define a nominal value.")


def _resolve_target_bounds(
    name: str,
    spec: Mapping[str, int | float],
    *,
    nominal: float,
    target_label: str,
) -> tuple[float | None, float, float]:
    if "minimum" in spec or "maximum" in spec:
        if "minimum" not in spec or "maximum" not in spec:
            raise ValueError(
                f"{target_label} {name!r} must define both minimum and maximum together."
            )
        tolerance_pct = float(spec["tolerance_pct"]) if "tolerance_pct" in spec else None
        return tolerance_pct, float(spec["minimum"]), float(spec["maximum"])

    if "tolerance_pct" not in spec:
        raise ValueError(
            f"{target_label} {name!r} must define either tolerance_pct or minimum/maximum."
        )
    tolerance_pct = float(spec["tolerance_pct"])
    minimum = nominal * (1.0 - (tolerance_pct / 100.0))
    maximum = nominal * (1.0 + (tolerance_pct / 100.0))
    return tolerance_pct, minimum, maximum


def normalize_target_specs(
    specs: Mapping[str, Mapping[str, int | float]] | None,
    *,
    target_kind: str,
    target_label: str,
    factory: Callable[[str, float, float | None, float, float], _TargetT],
    nominal_resolver: Callable[[str], float] | None = None,
) -> tuple[_TargetT, ...]:
    """Normalize one named target mapping into persisted statistical targets."""

    if not specs:
        return ()

    normalized: list[_TargetT] = []
    for name, spec in specs.items():
        nominal = _resolve_target_nominal(
            name,
            spec,
            target_label=target_label,
            nominal_resolver=nominal_resolver,
        )
        tolerance_pct, minimum, maximum = _resolve_target_bounds(
            name,
            spec,
            nominal=nominal,
            target_label=target_label,
        )

        if tolerance_pct is not None and tolerance_pct < 0:
            raise ValueError(f"{target_label} {name!r} must use a non-negative tolerance_pct.")
        if minimum > maximum:
            raise ValueError(f"{target_label} {name!r} must use minimum <= maximum.")
        if nominal < minimum or nominal > maximum:
            raise ValueError(
                f"{target_label} {name!r} must keep nominal within the provided bounds."
            )

        normalized.append(factory(name, nominal, tolerance_pct, minimum, maximum))
    return tuple(normalized)


def parse_spice_numeric_value(raw_value: object) -> float:
    """Parse one scalar SPICE-style value string into a float."""

    value_text = str(raw_value).strip()
    if not value_text:
        raise ValueError("Component values must not be empty.")
    if value_text.startswith("{") or value_text.lower().startswith("mc("):
        raise ValueError("Component values expressed as formulas need an explicit nominal.")

    match = fullmatch(_SPICE_NUMBER_PATTERN, value_text)
    if match is None:
        raise ValueError(f"Unsupported component value text: {value_text!r}")

    magnitude = float(match.group(1))
    suffix_text = match.group(2).lower()
    if not suffix_text:
        return magnitude
    for token, factor in _SPICE_SUFFIX_FACTORS:
        if suffix_text.startswith(token):
            return magnitude * factor
    raise ValueError(f"Unsupported component value suffix: {value_text!r}")


def build_schematic_component_nominal_resolver(
    source_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[Callable[[str], float], tuple[str, ...]]:
    """Build a resolver for component nominals read from the source schematic."""

    editor, _, _ = open_schematic_editor(source_path, workspace_root=workspace_root)
    references = tuple(str(reference) for reference in editor.get_components(prefixes="*"))
    value_text_by_reference = {
        reference: str(editor.get_component_value(reference)) for reference in references
    }
    cached_nominals: dict[str, float] = {}

    def _resolve(reference: str) -> float:
        try:
            raw_value = value_text_by_reference[reference]
        except KeyError as exc:
            raise ValueError(
                f"Component value {reference!r} was not found in the source schematic."
            ) from exc
        if reference not in cached_nominals:
            try:
                cached_nominals[reference] = parse_spice_numeric_value(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"Component value {reference!r} uses non-numeric schematic text "
                    f"{raw_value!r}; provide an explicit nominal."
                ) from exc
        return cached_nominals[reference]

    return _resolve, references


def expand_component_presets(
    component_presets: Mapping[str, Mapping[str, int | float]] | None,
    *,
    references: Sequence[str],
    explicit_references: frozenset[str],
) -> tuple[dict[str, dict[str, float]], tuple[str, ...]]:
    """Expand per-prefix component presets into explicit per-reference specs."""

    if not component_presets:
        return {}, ()

    expanded: dict[str, dict[str, float]] = {}
    warnings: list[str] = []
    for prefix, spec in component_presets.items():
        normalized_prefix = prefix.strip()
        if not normalized_prefix:
            raise ValueError("Component preset prefixes must not be empty.")
        if "tolerance_pct" not in spec:
            raise ValueError(f"Component preset {prefix!r} must define a tolerance_pct value.")
        tolerance_pct = float(spec["tolerance_pct"])
        if tolerance_pct < 0:
            raise ValueError(f"Component preset {prefix!r} must use a non-negative tolerance_pct.")

        matching_references = tuple(
            reference
            for reference in references
            if reference.upper().startswith(normalized_prefix.upper())
        )
        if not matching_references:
            raise ValueError(
                f"Component preset {prefix!r} did not match any source schematic references."
            )

        expanded_count = 0
        overridden_count = 0
        for reference in matching_references:
            if reference in explicit_references:
                overridden_count += 1
                continue
            if reference in expanded:
                raise ValueError(
                    f"Component preset {prefix!r} overlaps another preset at {reference!r}; "
                    "use explicit component_values to disambiguate."
                )
            expanded[reference] = {"tolerance_pct": tolerance_pct}
            expanded_count += 1

        warning = f"Expanded component preset {prefix!r} to {expanded_count} reference(s)."
        if overridden_count:
            warning = (
                f"{warning} Explicit component overrides took precedence for "
                f"{overridden_count} reference(s)."
            )
        warnings.append(warning)
    return expanded, tuple(warnings)


def resolve_component_target_specs(
    source_path: str | Path,
    *,
    workspace_root: Path,
    component_values: Mapping[str, Mapping[str, int | float]] | None,
    component_presets: Mapping[str, Mapping[str, int | float]] | None,
) -> tuple[
    dict[str, dict[str, int | float]],
    Callable[[str], float] | None,
    tuple[str, ...],
]:
    """Merge explicit component specs with per-prefix preset expansion."""

    explicit_specs = {
        str(reference): dict(spec) for reference, spec in dict(component_values or {}).items()
    }
    needs_nominal_resolver = bool(component_presets) or any(
        "nominal" not in spec for spec in explicit_specs.values()
    )
    if not needs_nominal_resolver:
        return explicit_specs, None, ()

    nominal_resolver, references = build_schematic_component_nominal_resolver(
        source_path,
        workspace_root=workspace_root,
    )
    expanded_specs, warnings = expand_component_presets(
        component_presets,
        references=references,
        explicit_references=frozenset(explicit_specs),
    )
    merged_specs: dict[str, dict[str, int | float]] = dict(expanded_specs)
    merged_specs.update(explicit_specs)
    return merged_specs, nominal_resolver, warnings


def build_native_mc_expression(*, nominal: float, tolerance_pct: float) -> str:
    """Render one QSPICE-native mc(nominal, fractional_tol) expression."""

    return (
        f"mc({_format_expression_number(nominal)}, "
        f"{_format_expression_number(tolerance_pct / 100.0)})"
    )


def build_assignment_payload(
    *,
    parameter_values: Mapping[str, float],
    component_values: Mapping[str, float],
) -> dict[str, object]:
    """Render one statistical assignment into a stable nested payload."""

    payload: dict[str, object] = {}
    if parameter_values:
        payload["parameters"] = dict(parameter_values)
    if component_values:
        payload["component_values"] = dict(component_values)
    return payload


def apply_assignment(
    editor: _QschEditorProtocol,
    *,
    parameter_values: Mapping[str, float],
    component_values: Mapping[str, float],
) -> None:
    """Apply one mixed parameter/component assignment to a schematic editor."""

    for name, value in parameter_values.items():
        editor.set_parameter(name, value)
    for reference, value in component_values.items():
        editor.set_component_value(reference, value)
