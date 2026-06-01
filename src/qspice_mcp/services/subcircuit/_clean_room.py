"""Clean-room helpers for backend-free subcircuit resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ArtifactMissingError, QSpiceError
from qspice_mcp.services._backends.clean_room_schematic import (
    CleanRoomComponentInspection,
    inspect_supported_schematic_components,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.subcircuit._navigation import (
    normalize_instance_path,
    normalize_subcircuit_reference,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _subcircuit_definition_candidate(definition_name: str | None) -> Path:
    normalized_definition = "" if definition_name is None else str(definition_name).strip()
    if not normalized_definition:
        raise QSpiceError(
            "Supported clean-room subcircuit resolution requires a non-empty component value."
        )
    if normalized_definition.lower().endswith(".qsch"):
        return Path(normalized_definition)
    return Path(f"{normalized_definition}.qsch")


def _candidate_definition_paths(
    parent_schematic_path: Path,
    *,
    workspace_root: Path,
    definition_name: str | None,
) -> tuple[Path, ...]:
    candidate = _subcircuit_definition_candidate(definition_name)
    if candidate.is_absolute():
        return (candidate,)

    parent_candidate = parent_schematic_path.parent / candidate
    workspace_candidate = workspace_root / candidate
    if workspace_candidate == parent_candidate:
        return (parent_candidate,)
    return (parent_candidate, workspace_candidate)


def resolve_supported_subcircuit_definition_path(
    parent_schematic_path: Path,
    *,
    workspace_root: Path,
    definition_name: str | None,
) -> Path:
    """Resolve one external clean-room subcircuit definition `.qsch` path."""

    last_missing_error: ArtifactMissingError | None = None
    for candidate in _candidate_definition_paths(
        parent_schematic_path,
        workspace_root=workspace_root,
        definition_name=definition_name,
    ):
        try:
            return validate_existing_file(
                candidate,
                workspace_root=workspace_root,
                suffixes=(".qsch",),
            )
        except ArtifactMissingError as exc:
            last_missing_error = exc

    if last_missing_error is not None:
        raise last_missing_error
    raise ArtifactMissingError(
        f"File not found: {_subcircuit_definition_candidate(definition_name)}"
    )


def _require_supported_subcircuit_component(
    components: tuple[CleanRoomComponentInspection, ...],
    *,
    reference: str,
) -> CleanRoomComponentInspection:
    for component in components:
        if component.reference != reference:
            continue
        if not component.has_subcircuit:
            raise QSpiceError(
                "Component "
                f"{reference} is not a subcircuit instance in the supported "
                "clean-room subset."
            )
        return component
    raise QSpiceError(
        "Subcircuit instance "
        f"{reference} was not found in the supported clean-room schematic "
        "subset."
    )


def resolve_supported_subcircuit_scope(
    schematic_path: Path,
    *,
    workspace_root: Path,
    instance_path: Sequence[str] | None = None,
) -> tuple[Path, tuple[str, ...], tuple[CleanRoomComponentInspection, ...]]:
    """Resolve one clean-room subcircuit scope to a supported `.qsch` definition."""

    normalized_instance_path = normalize_instance_path(instance_path)
    current_schematic_path = schematic_path
    traversed_path: list[str] = []
    for reference in normalized_instance_path:
        try:
            current_components = inspect_supported_schematic_components(current_schematic_path)
            component = _require_supported_subcircuit_component(
                current_components,
                reference=reference,
            )
            current_schematic_path = resolve_supported_subcircuit_definition_path(
                current_schematic_path,
                workspace_root=workspace_root,
                definition_name=component.value,
            )
        except Exception as exc:
            traversed = " -> ".join((*traversed_path, reference))
            raise QSpiceError(f"Failed to resolve subcircuit path {traversed}: {exc}") from exc
        traversed_path.append(reference)
    return (
        current_schematic_path,
        normalized_instance_path,
        inspect_supported_schematic_components(current_schematic_path),
    )


def resolve_supported_subcircuit_target(
    schematic_path: Path,
    *,
    workspace_root: Path,
    reference: str,
    instance_path: Sequence[str] | None = None,
) -> tuple[
    CleanRoomComponentInspection,
    Path,
    tuple[str, ...],
    tuple[CleanRoomComponentInspection, ...],
]:
    """Resolve one supported clean-room subcircuit target and inspect its definition."""

    scope_schematic_path, normalized_instance_path, scope_components = (
        resolve_supported_subcircuit_scope(
            schematic_path,
            workspace_root=workspace_root,
            instance_path=instance_path,
        )
    )
    normalized_reference = normalize_subcircuit_reference(reference)
    try:
        component = _require_supported_subcircuit_component(
            scope_components,
            reference=normalized_reference,
        )
        definition_path = resolve_supported_subcircuit_definition_path(
            scope_schematic_path,
            workspace_root=workspace_root,
            definition_name=component.value,
        )
    except Exception as exc:
        full_path = " -> ".join((*normalized_instance_path, normalized_reference))
        raise QSpiceError(f"Failed to resolve subcircuit path {full_path}: {exc}") from exc
    return (
        component,
        definition_path,
        normalized_instance_path,
        inspect_supported_schematic_components(definition_path),
    )


__all__ = [
    "resolve_supported_subcircuit_definition_path",
    "resolve_supported_subcircuit_scope",
    "resolve_supported_subcircuit_target",
]
