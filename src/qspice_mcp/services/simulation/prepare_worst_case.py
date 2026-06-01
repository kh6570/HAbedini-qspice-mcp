"""Service for preparing explicit worst-case parameter and component cases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._statistical_helpers import (
    normalize_target_specs,
    resolve_component_target_specs,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

WorstCaseMode = Literal["corners", "one_at_a_time"]
_MAX_CORNER_CASES = 256


@dataclass(frozen=True, slots=True)
class WorstCaseParameter:
    """One schematic parameter varied in worst-case preparation."""

    name: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    kind: Literal["parameter"] = "parameter"


@dataclass(frozen=True, slots=True)
class WorstCaseComponentValue:
    """One component reference varied in worst-case preparation."""

    reference: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    kind: Literal["component_value"] = "component_value"


@dataclass(frozen=True, slots=True)
class WorstCaseCase:
    """One explicit worst-case assignment."""

    index: int
    parameter_values: dict[str, float]
    component_values: dict[str, float]
    label: str

    @property
    def values(self) -> dict[str, float]:
        merged = dict(self.parameter_values)
        for reference, value in self.component_values.items():
            merged.setdefault(reference, value)
        return merged


@dataclass(frozen=True, slots=True)
class PreparedWorstCase:
    """Persisted explicit worst-case plan metadata."""

    source_path: Path
    plan_path: Path
    output_root: Path
    mode: WorstCaseMode
    include_nominal: bool
    parameters: tuple[WorstCaseParameter, ...]
    cases: tuple[WorstCaseCase, ...]
    component_values: tuple[WorstCaseComponentValue, ...] = ()
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_worst_case",
    title="Prepare Worst Case",
    summary="Prepare explicit worst-case corner assignments for later execution.",
    phase="implemented",
    read_only=False,
)


def _default_output_root(source_path: Path, *, workspace_root: Path) -> Path:
    return (
        workspace_root / "artifacts" / "statistical" / f"{source_path.stem}-worst-case"
    ).resolve(strict=False)


def _resolve_plan_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    source_path: Path,
) -> tuple[Path, Path]:
    if output_path is None:
        output_root = _default_output_root(source_path, workspace_root=workspace_root)
        return output_root / "plan.json", output_root

    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() != ".json":
        raise ValueError("output_path must end in .json")
    return resolved, resolved.parent.resolve(strict=False)


def _normalize_parameters(
    parameters: Mapping[str, Mapping[str, int | float]] | None,
) -> tuple[WorstCaseParameter, ...]:
    return normalize_target_specs(
        parameters,
        target_kind="parameter",
        target_label="Parameter",
        factory=lambda name, nominal, tolerance_pct, minimum, maximum: WorstCaseParameter(
            name=name,
            nominal=nominal,
            tolerance_pct=tolerance_pct,
            minimum=minimum,
            maximum=maximum,
        ),
    )


def _normalize_component_values(
    component_values: Mapping[str, Mapping[str, int | float]] | None,
    *,
    nominal_resolver: Callable[[str], float] | None = None,
) -> tuple[WorstCaseComponentValue, ...]:
    return normalize_target_specs(
        component_values,
        target_kind="component_value",
        target_label="Component value",
        factory=lambda name, nominal, tolerance_pct, minimum, maximum: WorstCaseComponentValue(
            reference=name,
            nominal=nominal,
            tolerance_pct=tolerance_pct,
            minimum=minimum,
            maximum=maximum,
        ),
        nominal_resolver=nominal_resolver,
    )


def _base_case_values(
    parameters: tuple[WorstCaseParameter, ...],
    component_values: tuple[WorstCaseComponentValue, ...],
) -> tuple[dict[str, float], dict[str, float]]:
    return (
        {parameter.name: parameter.nominal for parameter in parameters},
        {component.reference: component.nominal for component in component_values},
    )


def _build_cases(
    parameters: tuple[WorstCaseParameter, ...],
    component_values: tuple[WorstCaseComponentValue, ...],
    *,
    mode: WorstCaseMode,
    include_nominal: bool,
) -> tuple[WorstCaseCase, ...]:
    target_defs: list[tuple[str, str, float, float, float]] = [
        ("parameter", parameter.name, parameter.nominal, parameter.minimum, parameter.maximum)
        for parameter in parameters
    ]
    target_defs.extend(
        (
            "component_value",
            component.reference,
            component.nominal,
            component.minimum,
            component.maximum,
        )
        for component in component_values
    )
    if not target_defs:
        raise ValueError(
            "prepare_worst_case requires at least one parameter or component value target."
        )

    base_parameter_values, base_component_values = _base_case_values(parameters, component_values)
    cases: list[WorstCaseCase] = []

    def append_case(
        *,
        label: str,
        parameter_values: dict[str, float],
        component_values: dict[str, float],
    ) -> None:
        cases.append(
            WorstCaseCase(
                index=len(cases),
                parameter_values=parameter_values,
                component_values=component_values,
                label=label,
            )
        )

    if include_nominal:
        append_case(
            label="nominal",
            parameter_values=dict(base_parameter_values),
            component_values=dict(base_component_values),
        )

    if mode == "one_at_a_time":
        for target_kind, name, _, minimum, maximum in target_defs:
            for bound_label, bound_value in (("min", minimum), ("max", maximum)):
                parameter_values = dict(base_parameter_values)
                component_value_map = dict(base_component_values)
                if target_kind == "parameter":
                    parameter_values[name] = bound_value
                else:
                    component_value_map[name] = bound_value
                append_case(
                    label=f"{name}-{bound_label}",
                    parameter_values=parameter_values,
                    component_values=component_value_map,
                )
        return tuple(cases)

    projected_case_count = (1 if include_nominal else 0) + (2 ** len(target_defs))
    if projected_case_count > _MAX_CORNER_CASES:
        raise ValueError(
            "prepare_worst_case would generate too many corner cases; reduce the target "
            "count or use mode='one_at_a_time'."
        )

    for combo_index, combo in enumerate(product(("min", "max"), repeat=len(target_defs))):
        parameter_values = dict(base_parameter_values)
        component_value_map = dict(base_component_values)
        for (target_kind, name, _, minimum, maximum), direction in zip(
            target_defs, combo, strict=True
        ):
            target_value = minimum if direction == "min" else maximum
            if target_kind == "parameter":
                parameter_values[name] = target_value
            else:
                component_value_map[name] = target_value
        append_case(
            label=f"corner-{combo_index:03d}",
            parameter_values=parameter_values,
            component_values=component_value_map,
        )
    return tuple(cases)


def save_prepared_worst_case(prepared: PreparedWorstCase) -> PreparedWorstCase:
    """Persist one worst-case plan artifact to JSON."""

    prepared.plan_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_path": str(prepared.source_path),
        "plan_path": str(prepared.plan_path),
        "output_root": str(prepared.output_root),
        "mode": prepared.mode,
        "include_nominal": prepared.include_nominal,
        "parameters": [
            {
                "name": parameter.name,
                "nominal": parameter.nominal,
                "tolerance_pct": parameter.tolerance_pct,
                "minimum": parameter.minimum,
                "maximum": parameter.maximum,
            }
            for parameter in prepared.parameters
        ],
        "component_values": [
            {
                "reference": component.reference,
                "nominal": component.nominal,
                "tolerance_pct": component.tolerance_pct,
                "minimum": component.minimum,
                "maximum": component.maximum,
            }
            for component in prepared.component_values
        ],
        "cases": [
            {
                "index": case.index,
                "parameter_values": dict(case.parameter_values),
                "component_values": dict(case.component_values),
                "label": case.label,
            }
            for case in prepared.cases
        ],
        "warnings": list(prepared.warnings),
    }
    prepared.plan_path.write_text(
        json.dumps(stamp_schema_version(payload), indent=2),
        encoding="utf-8",
    )
    return prepared


def load_prepared_worst_case(
    plan_path: str | Path,
    *,
    workspace_root: Path,
) -> PreparedWorstCase:
    """Load one persisted worst-case plan artifact from JSON."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved = validate_existing_file(
        plan_path,
        workspace_root=normalized_workspace,
        suffixes=(".json",),
    )
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    validate_schema_version(
        payload,
        artifact_name="Worst-case plan",
        allow_legacy_unversioned=True,
    )

    def resolve_persisted_path(value: object) -> Path:
        return resolve_workspace_path(str(value), workspace_root=normalized_workspace)

    return PreparedWorstCase(
        source_path=resolve_persisted_path(payload["source_path"]),
        plan_path=resolved,
        output_root=resolve_persisted_path(payload["output_root"]),
        mode=payload.get("mode", "corners"),
        include_nominal=bool(payload.get("include_nominal", True)),
        parameters=tuple(
            WorstCaseParameter(
                name=str(parameter["name"]),
                nominal=float(parameter["nominal"]),
                tolerance_pct=(
                    None
                    if parameter.get("tolerance_pct") is None
                    else float(parameter["tolerance_pct"])
                ),
                minimum=float(parameter["minimum"]),
                maximum=float(parameter["maximum"]),
            )
            for parameter in payload.get("parameters", ())
        ),
        cases=tuple(
            WorstCaseCase(
                index=int(case["index"]),
                parameter_values={
                    str(name): float(value)
                    for name, value in dict(case.get("parameter_values", {})).items()
                },
                component_values={
                    str(reference): float(value)
                    for reference, value in dict(case.get("component_values", {})).items()
                },
                label=str(case["label"]),
            )
            for case in payload.get("cases", ())
        ),
        component_values=tuple(
            WorstCaseComponentValue(
                reference=str(component["reference"]),
                nominal=float(component["nominal"]),
                tolerance_pct=(
                    None
                    if component.get("tolerance_pct") is None
                    else float(component["tolerance_pct"])
                ),
                minimum=float(component["minimum"]),
                maximum=float(component["maximum"]),
            )
            for component in payload.get("component_values", ())
        ),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
    )


def prepare_worst_case(
    source_path: str | Path,
    *,
    workspace_root: Path,
    parameters: Mapping[str, Mapping[str, int | float]] | None = None,
    component_values: Mapping[str, Mapping[str, int | float]] | None = None,
    component_presets: Mapping[str, Mapping[str, int | float]] | None = None,
    mode: WorstCaseMode = "corners",
    include_nominal: bool = True,
    output_path: str | Path | None = None,
) -> PreparedWorstCase:
    """Persist explicit worst-case assignments for later execution."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch",),
    )
    normalized_parameters = _normalize_parameters(parameters)
    component_specs, component_nominal_resolver, preset_warnings = resolve_component_target_specs(
        resolved_source,
        workspace_root=normalized_workspace,
        component_values=component_values,
        component_presets=component_presets,
    )
    normalized_component_values = _normalize_component_values(
        component_specs,
        nominal_resolver=component_nominal_resolver,
    )
    cases = _build_cases(
        normalized_parameters,
        normalized_component_values,
        mode=mode,
        include_nominal=include_nominal,
    )
    plan_path, output_root = _resolve_plan_path(
        output_path,
        workspace_root=normalized_workspace,
        source_path=resolved_source,
    )
    prepared = PreparedWorstCase(
        source_path=resolved_source,
        plan_path=plan_path.resolve(strict=False),
        output_root=output_root,
        mode=mode,
        include_nominal=include_nominal,
        parameters=normalized_parameters,
        cases=cases,
        component_values=normalized_component_values,
        warnings=tuple(
            dict.fromkeys(
                (
                    "Prepared explicit worst-case assignments; run_worst_case stages "
                    "copy-on-write schematic artifacts per case.",
                    *preset_warnings,
                )
            )
        ),
    )
    return save_prepared_worst_case(prepared)


__all__ = [
    "SERVICE_SPEC",
    "PreparedWorstCase",
    "WorstCaseCase",
    "WorstCaseComponentValue",
    "WorstCaseMode",
    "WorstCaseParameter",
    "load_prepared_worst_case",
    "prepare_worst_case",
    "save_prepared_worst_case",
]
