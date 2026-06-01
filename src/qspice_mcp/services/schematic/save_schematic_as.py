"""Service for saving a schematic to a new `.qsch` path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class SavedSchematic:
    """Metadata for one saved schematic artifact."""

    schematic_path: Path
    output_path: Path


SERVICE_SPEC = ServiceSpec(
    name="save_schematic_as",
    title="Save Schematic As",
    summary="Write a schematic to a requested `.qsch` path through an installed editor backend.",
    phase="implemented",
    read_only=False,
)


def save_schematic_as(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path,
) -> SavedSchematic:
    """Save a schematic to a requested destination path."""

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return SavedSchematic(schematic_path=resolved_path, output_path=saved_path)


__all__ = ["SERVICE_SPEC", "SavedSchematic", "save_schematic_as"]
