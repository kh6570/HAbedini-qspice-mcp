"""Service for enumerating subcircuit instances from a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.subcircuit._clean_room import (
    resolve_supported_subcircuit_scope,
    resolve_supported_subcircuit_target,
)
from qspice_mcp.services.subcircuit._navigation import (
    normalize_instance_path,
    resolve_subcircuit_scope_editor,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SubcircuitSummary:
    """A normalized summary of one subcircuit instance."""

    reference: str
    definition_name: str | None
    description: str | None
    definition_available: bool
    component_count: int | None
    definition_resolution_error: str | None = None


@dataclass(frozen=True, slots=True)
class SubcircuitCatalog:
    """Subcircuit inventory for one schematic."""

    schematic_path: Path
    instance_path: tuple[str, ...]
    subcircuit_count: int
    subcircuits: tuple[SubcircuitSummary, ...]


SERVICE_SPEC = ServiceSpec(
    name="list_subcircuits",
    title="List Subcircuits",
    summary="Enumerate subcircuit instances referenced by a schematic.",
    phase="implemented",
)


def list_subcircuits(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    instance_path: tuple[str, ...] | list[str] | None = None,
) -> SubcircuitCatalog:
    """Enumerate subcircuit instances that appear in one schematic."""

    resolved_workspace = workspace_root.resolve(strict=False)
    normalized_instance_path = normalize_instance_path(instance_path)
    subcircuits: list[SubcircuitSummary] = []
    try:
        editor, resolved_path, _ = open_schematic_editor(
            schematic_path,
            workspace_root=resolved_workspace,
        )
    except BackendUnavailableError:
        resolved_path = validate_existing_file(
            schematic_path,
            workspace_root=resolved_workspace,
            suffixes=(".qsch",),
        )
        _, normalized_instance_path, parsed_components = resolve_supported_subcircuit_scope(
            resolved_path,
            workspace_root=resolved_workspace,
            instance_path=normalized_instance_path,
        )
        for parsed_component in parsed_components:
            if not parsed_component.has_subcircuit:
                continue
            try:
                _, _, _, definition_components = resolve_supported_subcircuit_target(
                    resolved_path,
                    workspace_root=resolved_workspace,
                    reference=parsed_component.reference,
                    instance_path=normalized_instance_path,
                )
                summary = SubcircuitSummary(
                    reference=parsed_component.reference,
                    definition_name=parsed_component.value,
                    description=parsed_component.description,
                    definition_available=True,
                    component_count=len(definition_components),
                )
            except Exception as exc:
                summary = SubcircuitSummary(
                    reference=parsed_component.reference,
                    definition_name=parsed_component.value,
                    description=parsed_component.description,
                    definition_available=False,
                    component_count=None,
                    definition_resolution_error=str(exc),
                )
            subcircuits.append(summary)
        return SubcircuitCatalog(
            schematic_path=resolved_path,
            instance_path=normalized_instance_path,
            subcircuit_count=len(subcircuits),
            subcircuits=tuple(subcircuits),
        )

    scope_editor, normalized_instance_path = resolve_subcircuit_scope_editor(
        editor,
        instance_path=normalized_instance_path,
    )
    references = tuple(str(reference) for reference in scope_editor.get_components(prefixes="X"))
    resolved_subcircuits: list[SubcircuitSummary] = []
    for reference in references:
        component = scope_editor.get_component(reference)
        attributes = dict(component.attributes)
        value = attributes.get("value")
        description = attributes.get("description")
        try:
            subeditor = scope_editor.get_subcircuit(reference)
            component_count = len(
                tuple(str(name) for name in subeditor.get_components(prefixes="*"))
            )
            summary = SubcircuitSummary(
                reference=reference,
                definition_name=str(value) if value is not None else None,
                description=str(description) if description is not None else None,
                definition_available=True,
                component_count=component_count,
            )
        except Exception as exc:
            summary = SubcircuitSummary(
                reference=reference,
                definition_name=str(value) if value is not None else None,
                description=str(description) if description is not None else None,
                definition_available=False,
                component_count=None,
                definition_resolution_error=str(exc),
            )
        resolved_subcircuits.append(summary)
    return SubcircuitCatalog(
        schematic_path=resolved_path,
        instance_path=normalized_instance_path,
        subcircuit_count=len(resolved_subcircuits),
        subcircuits=tuple(resolved_subcircuits),
    )


__all__ = ["SERVICE_SPEC", "SubcircuitCatalog", "SubcircuitSummary", "list_subcircuits"]
