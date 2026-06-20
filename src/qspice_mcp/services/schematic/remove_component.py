"""Service for removing one component from a schematic by reference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@dataclass(frozen=True, slots=True)
class RemovedComponent:
    """Metadata for one component removal."""

    schematic_path: Path
    output_path: Path
    reference: str


SERVICE_SPEC = ServiceSpec(
    name="remove_component",
    title="Remove Component",
    summary="Remove one schematic component by reference and persist the edited schematic.",
    phase="implemented",
    read_only=False,
    destructive=True,
)


def remove_component(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    output_path: str | Path | None = None,
) -> RemovedComponent:
    """Remove one component by reference and persist the edited schematic."""

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=lambda editor: _apply_remove_edit(editor, reference),
    )
    return RemovedComponent(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
    )


def _apply_remove_edit(editor: Any, reference: str) -> None:
    editor.remove_component(reference)
    editor.updated = True


__all__ = ["SERVICE_SPEC", "RemovedComponent", "remove_component"]
