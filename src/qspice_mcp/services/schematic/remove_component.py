"""Service for removing one component from a schematic by reference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import (
    remove_component_with_orphan_cleanup,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RemovedComponent:
    """Metadata for one component removal."""

    schematic_path: Path
    output_path: Path
    reference: str
    remove_orphan_wires: bool = False
    wires_removed: int = 0
    junctions_removed: int = 0
    net_labels_removed: int = 0


SERVICE_SPEC = ServiceSpec(
    name="remove_component",
    title="Remove Component",
    summary=(
        "Remove one schematic component by reference. Optionally prune wires, junctions, "
        "and net labels left dangling by the deletion (remove_orphan_wires, opt-in)."
    ),
    phase="implemented",
    read_only=False,
    destructive=True,
)


def remove_component(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    remove_orphan_wires: bool = False,
    output_path: str | Path | None = None,
) -> RemovedComponent:
    """Remove one component by reference and persist the edited schematic."""

    cleanup: Any = None

    def apply_remove_edit(editor: object) -> None:
        nonlocal cleanup
        cleanup = remove_component_with_orphan_cleanup(
            cast("Any", editor),
            reference=reference,
            remove_orphan_wires=remove_orphan_wires,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_remove_edit,
    )
    wires_removed = cleanup.wires_removed if cleanup is not None else 0
    junctions_removed = cleanup.junctions_removed if cleanup is not None else 0
    net_labels_removed = cleanup.net_labels_removed if cleanup is not None else 0
    return RemovedComponent(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        remove_orphan_wires=remove_orphan_wires,
        wires_removed=wires_removed,
        junctions_removed=junctions_removed,
        net_labels_removed=net_labels_removed,
    )


__all__ = ["SERVICE_SPEC", "RemovedComponent", "remove_component"]
