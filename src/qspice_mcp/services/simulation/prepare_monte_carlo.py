"""Service for preparing explicit Monte Carlo parameter samples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from random import Random
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._internals.persistence_schema import (
    stamp_schema_version,
    validate_schema_version,
)
from qspice_mcp.services._internals.schematic_edits import save_edited_schematic
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._statistical_helpers import (
    build_native_mc_expression,
    normalize_target_specs,
    resolve_component_target_specs,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class MonteCarloParameter:
    """One parameter varied across Monte Carlo samples."""

    name: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    kind: Literal["parameter"] = "parameter"


@dataclass(frozen=True, slots=True)
class MonteCarloComponentValue:
    """One component reference varied across Monte Carlo samples."""

    reference: str
    nominal: float
    tolerance_pct: float | None
    minimum: float
    maximum: float
    kind: Literal["component_value"] = "component_value"


@dataclass(frozen=True, slots=True)
class MonteCarloSample:
    """One explicit Monte Carlo parameter assignment."""

    index: int
    parameter_values: dict[str, float]
    component_values: dict[str, float]
    label: str | None = None

    @property
    def values(self) -> dict[str, float]:
        """Return a merged view of target values for compatibility."""

        merged = dict(self.parameter_values)
        for reference, value in self.component_values.items():
            merged.setdefault(reference, value)
        return merged


@dataclass(frozen=True, slots=True)
class NativeMonteCarloStage:
    """Optional staged schematic that uses QSPICE-native mc(...) expressions."""

    schematic_path: Path
    parameter_expressions: dict[str, str]
    component_value_expressions: dict[str, str]


@dataclass(frozen=True, slots=True)
class PreparedMonteCarlo:
    """Persisted explicit Monte Carlo plan metadata."""

    source_path: Path
    plan_path: Path
    output_root: Path
    sample_count: int
    seed: int
    distribution: Literal["uniform"]
    parameters: tuple[MonteCarloParameter, ...]
    samples: tuple[MonteCarloSample, ...]
    component_values: tuple[MonteCarloComponentValue, ...] = ()
    native_mc_stage: NativeMonteCarloStage | None = None
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_monte_carlo",
    title="Prepare Monte Carlo",
    summary=(
        "Prepare an explicit Monte Carlo parameter plan with persisted per-sample assignments."
    ),
    phase="implemented",
    read_only=False,
)


def _default_output_root(source_path: Path, *, workspace_root: Path) -> Path:
    return (
        workspace_root / "artifacts" / "statistical" / f"{source_path.stem}-monte-carlo"
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
) -> tuple[MonteCarloParameter, ...]:
    return normalize_target_specs(
        parameters,
        target_kind="parameter",
        target_label="Parameter",
        factory=lambda name, nominal, tolerance_pct, minimum, maximum: MonteCarloParameter(
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
) -> tuple[MonteCarloComponentValue, ...]:
    return normalize_target_specs(
        component_values,
        target_kind="component_value",
        target_label="Component value",
        factory=lambda name, nominal, tolerance_pct, minimum, maximum: MonteCarloComponentValue(
            reference=name,
            nominal=nominal,
            tolerance_pct=tolerance_pct,
            minimum=minimum,
            maximum=maximum,
        ),
        nominal_resolver=nominal_resolver,
    )


def _build_samples(
    parameters: tuple[MonteCarloParameter, ...],
    component_values: tuple[MonteCarloComponentValue, ...],
    *,
    sample_count: int,
    seed: int,
) -> tuple[MonteCarloSample, ...]:
    if sample_count < 1:
        raise ValueError("sample_count must be at least 1")

    rng = Random(seed)  # noqa: S311 - deterministic Monte Carlo sampling is intentional.
    samples: list[MonteCarloSample] = []
    for index in range(sample_count):
        parameter_values = {
            parameter.name: rng.uniform(parameter.minimum, parameter.maximum)
            for parameter in parameters
        }
        sampled_component_values = {
            component.reference: rng.uniform(component.minimum, component.maximum)
            for component in component_values
        }
        samples.append(
            MonteCarloSample(
                index=index,
                parameter_values=parameter_values,
                component_values=sampled_component_values,
                label=f"sample-{index:03d}",
            )
        )
    return tuple(samples)


def _default_native_mc_stage_path(output_root: Path, source_path: Path) -> Path:
    return (output_root / "native-mc" / source_path.name).resolve(strict=False)


def _build_native_mc_stage(
    *,
    source_path: Path,
    workspace_root: Path,
    output_root: Path,
    parameters: tuple[MonteCarloParameter, ...],
    component_values: tuple[MonteCarloComponentValue, ...],
) -> NativeMonteCarloStage:
    parameter_expressions: dict[str, str] = {}
    for parameter in parameters:
        if parameter.tolerance_pct is None:
            raise ValueError("stage_native_mc requires tolerance_pct for every parameter target.")
        parameter_expressions[parameter.name] = build_native_mc_expression(
            nominal=parameter.nominal,
            tolerance_pct=parameter.tolerance_pct,
        )

    component_value_expressions: dict[str, str] = {}
    for component in component_values:
        if component.tolerance_pct is None:
            raise ValueError(
                "stage_native_mc requires tolerance_pct for every component value target."
            )
        component_value_expressions[component.reference] = build_native_mc_expression(
            nominal=component.nominal,
            tolerance_pct=component.tolerance_pct,
        )

    editor, resolved_source, _ = open_schematic_editor(source_path, workspace_root=workspace_root)
    for name, expression in parameter_expressions.items():
        editor.set_parameter(name, expression)
    for reference, expression in component_value_expressions.items():
        editor.set_component_value(reference, expression)

    staged_path = save_edited_schematic(
        editor,
        schematic_path=resolved_source,
        workspace_root=workspace_root,
        output_path=_default_native_mc_stage_path(output_root, resolved_source),
    )
    return NativeMonteCarloStage(
        schematic_path=staged_path,
        parameter_expressions=parameter_expressions,
        component_value_expressions=component_value_expressions,
    )


def save_prepared_monte_carlo(prepared: PreparedMonteCarlo) -> PreparedMonteCarlo:
    """Persist one Monte Carlo plan artifact to JSON."""

    prepared.plan_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source_path": str(prepared.source_path),
        "plan_path": str(prepared.plan_path),
        "output_root": str(prepared.output_root),
        "sample_count": prepared.sample_count,
        "seed": prepared.seed,
        "distribution": prepared.distribution,
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
        "samples": [
            {
                "index": sample.index,
                "parameter_values": dict(sample.parameter_values),
                "component_values": dict(sample.component_values),
                "label": sample.label,
            }
            for sample in prepared.samples
        ],
        "native_mc_stage": (
            None
            if prepared.native_mc_stage is None
            else {
                "schematic_path": str(prepared.native_mc_stage.schematic_path),
                "parameter_expressions": dict(prepared.native_mc_stage.parameter_expressions),
                "component_value_expressions": dict(
                    prepared.native_mc_stage.component_value_expressions
                ),
            }
        ),
        "warnings": list(prepared.warnings),
    }
    prepared.plan_path.write_text(
        json.dumps(stamp_schema_version(payload), indent=2),
        encoding="utf-8",
    )
    return prepared


def load_prepared_monte_carlo(
    plan_path: str | Path,
    *,
    workspace_root: Path,
) -> PreparedMonteCarlo:
    """Load one persisted Monte Carlo plan artifact from JSON."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved = validate_existing_file(
        plan_path,
        workspace_root=normalized_workspace,
        suffixes=(".json",),
    )
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    validate_schema_version(
        payload,
        artifact_name="Monte Carlo plan",
        allow_legacy_unversioned=True,
    )

    def resolve_persisted_path(value: object) -> Path:
        return resolve_workspace_path(str(value), workspace_root=normalized_workspace)

    return PreparedMonteCarlo(
        source_path=resolve_persisted_path(payload["source_path"]),
        plan_path=resolved,
        output_root=resolve_persisted_path(payload["output_root"]),
        sample_count=int(payload["sample_count"]),
        seed=int(payload["seed"]),
        distribution=payload.get("distribution", "uniform"),
        parameters=tuple(
            MonteCarloParameter(
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
        component_values=tuple(
            MonteCarloComponentValue(
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
        native_mc_stage=(
            None
            if payload.get("native_mc_stage") is None
            else NativeMonteCarloStage(
                schematic_path=resolve_persisted_path(payload["native_mc_stage"]["schematic_path"]),
                parameter_expressions={
                    str(name): str(value)
                    for name, value in dict(
                        payload["native_mc_stage"].get("parameter_expressions", {})
                    ).items()
                },
                component_value_expressions={
                    str(reference): str(value)
                    for reference, value in dict(
                        payload["native_mc_stage"].get("component_value_expressions", {})
                    ).items()
                },
            )
        ),
        samples=tuple(
            MonteCarloSample(
                index=int(sample["index"]),
                parameter_values={
                    str(name): float(value)
                    for name, value in dict(
                        sample.get("parameter_values", sample.get("values", {}))
                    ).items()
                },
                component_values={
                    str(reference): float(value)
                    for reference, value in dict(sample.get("component_values", {})).items()
                },
                label=None if sample.get("label") is None else str(sample["label"]),
            )
            for sample in payload.get("samples", ())
        ),
        warnings=tuple(str(value) for value in payload.get("warnings", ())),
    )


def prepare_monte_carlo(
    source_path: str | Path,
    *,
    workspace_root: Path,
    parameters: Mapping[str, Mapping[str, int | float]] | None = None,
    component_values: Mapping[str, Mapping[str, int | float]] | None = None,
    component_presets: Mapping[str, Mapping[str, int | float]] | None = None,
    sample_count: int,
    seed: int = 0,
    stage_native_mc: bool = False,
    output_path: str | Path | None = None,
) -> PreparedMonteCarlo:
    """Persist explicit Monte Carlo parameter assignments for later execution."""

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
    if not normalized_parameters and not normalized_component_values:
        raise ValueError(
            "prepare_monte_carlo requires at least one parameter or component value target."
        )
    samples = _build_samples(
        normalized_parameters,
        normalized_component_values,
        sample_count=sample_count,
        seed=seed,
    )
    plan_path, output_root = _resolve_plan_path(
        output_path,
        workspace_root=normalized_workspace,
        source_path=resolved_source,
    )
    native_mc_stage = (
        _build_native_mc_stage(
            source_path=resolved_source,
            workspace_root=normalized_workspace,
            output_root=output_root,
            parameters=normalized_parameters,
            component_values=normalized_component_values,
        )
        if stage_native_mc
        else None
    )
    prepared = PreparedMonteCarlo(
        source_path=resolved_source,
        plan_path=plan_path.resolve(strict=False),
        output_root=output_root,
        sample_count=sample_count,
        seed=seed,
        distribution="uniform",
        parameters=normalized_parameters,
        component_values=normalized_component_values,
        samples=samples,
        native_mc_stage=native_mc_stage,
        warnings=tuple(
            dict.fromkeys(
                (
                    "Prepared explicit statistical assignments; run_monte_carlo stages "
                    "copy-on-write schematic artifacts per sample.",
                    *preset_warnings,
                    *(
                        (
                            "Staged an optional native Monte Carlo schematic that uses "
                            "QSPICE mc(...) expressions for inspection."
                        )
                        if native_mc_stage is not None
                        else ()
                    ),
                )
            )
        ),
    )
    return save_prepared_monte_carlo(prepared)


__all__ = [
    "SERVICE_SPEC",
    "MonteCarloComponentValue",
    "MonteCarloParameter",
    "MonteCarloSample",
    "NativeMonteCarloStage",
    "PreparedMonteCarlo",
    "load_prepared_monte_carlo",
    "prepare_monte_carlo",
    "save_prepared_monte_carlo",
]
