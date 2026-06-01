"""Shared helpers for nested subcircuit navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import QSpiceError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


def normalize_instance_path(instance_path: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize one optional nested subcircuit path."""

    normalized_path: list[str] = []
    for segment in instance_path or ():
        normalized_segment = str(segment).strip()
        if not normalized_segment:
            raise ValueError("instance_path must not contain empty reference segments")
        normalized_path.append(normalized_segment)
    return tuple(normalized_path)


def normalize_subcircuit_reference(reference: str) -> str:
    """Normalize one selected subcircuit reference."""

    normalized = reference.strip()
    if not normalized:
        raise ValueError("reference must not be empty")
    return normalized


def normalize_component_reference(component_reference: str) -> str:
    """Normalize one selected nested component reference."""

    normalized = component_reference.strip()
    if not normalized:
        raise ValueError("component_reference must not be empty")
    return normalized


def resolve_subcircuit_scope_editor(
    editor: _QschEditorProtocol,
    *,
    instance_path: Sequence[str] | None = None,
) -> tuple[_QschEditorProtocol, tuple[str, ...]]:
    """Resolve one optional nested subcircuit scope path to an editor."""

    resolved_path = normalize_instance_path(instance_path)
    current_editor = editor
    traversed_path: list[str] = []
    for reference in resolved_path:
        try:
            current_editor = current_editor.get_subcircuit(reference)
        except Exception as exc:
            traversed = " -> ".join((*traversed_path, reference))
            raise QSpiceError(f"Failed to resolve subcircuit path {traversed}: {exc}") from exc
        traversed_path.append(reference)
    return current_editor, resolved_path


def resolve_subcircuit_target(
    editor: _QschEditorProtocol,
    *,
    reference: str,
    instance_path: Sequence[str] | None = None,
) -> tuple[_QschEditorProtocol, _QschEditorProtocol, tuple[str, ...], str]:
    """Resolve one selected subcircuit relative to an optional parent path."""

    parent_editor, normalized_instance_path = resolve_subcircuit_scope_editor(
        editor,
        instance_path=instance_path,
    )
    normalized_reference = normalize_subcircuit_reference(reference)
    try:
        subeditor = parent_editor.get_subcircuit(normalized_reference)
    except Exception as exc:
        full_path = " -> ".join((*normalized_instance_path, normalized_reference))
        raise QSpiceError(f"Failed to resolve subcircuit path {full_path}: {exc}") from exc
    return parent_editor, subeditor, normalized_instance_path, normalized_reference


def build_instance_component_reference(
    *,
    reference: str,
    component_reference: str,
    instance_path: Sequence[str] | None = None,
) -> str:
    """Compose one hierarchical instance-scoped component selector."""

    hierarchy = [
        *normalize_instance_path(instance_path),
        normalize_subcircuit_reference(reference),
        normalize_component_reference(component_reference),
    ]
    return ":".join(hierarchy)


def split_instance_component_reference(
    component_reference: str,
) -> tuple[tuple[str, ...], str, str]:
    """Split one hierarchical instance-scoped component selector."""

    normalized = normalize_component_reference(component_reference)
    hierarchy = tuple(segment.strip() for segment in normalized.split(":"))
    if len(hierarchy) < 2:  # noqa: PLR2004
        raise ValueError(
            "component_reference must include a subcircuit and component segment, for example X1:R1"
        )
    normalized_instance_path = normalize_instance_path(hierarchy[:-2])
    normalized_reference = normalize_subcircuit_reference(hierarchy[-2])
    normalized_component_reference = normalize_component_reference(hierarchy[-1])
    return normalized_instance_path, normalized_reference, normalized_component_reference


def default_definition_output_name(
    *,
    reference: str,
    instance_path: Sequence[str] | None = None,
) -> str:
    """Return the default filename stem for one definition-scoped save."""

    hierarchy = [*normalize_instance_path(instance_path), normalize_subcircuit_reference(reference)]
    return f"{'-'.join(hierarchy)}-definition.qsch"


__all__ = [
    "build_instance_component_reference",
    "default_definition_output_name",
    "normalize_component_reference",
    "normalize_instance_path",
    "normalize_subcircuit_reference",
    "resolve_subcircuit_scope_editor",
    "resolve_subcircuit_target",
    "split_instance_component_reference",
]
