"""Service for creating a blank schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import create_blank_schematic_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class CreatedSchematic:
    """Metadata for one newly created blank schematic."""

    output_path: Path
    overwritten: bool


SERVICE_SPEC = ServiceSpec(
    name="create_schematic",
    title="Create Schematic",
    summary="Create a blank `.qsch` file so later schematic tools can build from scratch.",
    phase="implemented",
    read_only=False,
)


def create_schematic(
    output_path: str | Path,
    *,
    workspace_root: Path,
    overwrite: bool = False,
) -> CreatedSchematic:
    """Create a blank schematic within the current workspace root."""

    saved_path, overwritten = create_blank_schematic_file(
        output_path,
        workspace_root=workspace_root,
        overwrite=overwrite,
    )
    return CreatedSchematic(output_path=saved_path, overwritten=overwritten)


__all__ = ["SERVICE_SPEC", "CreatedSchematic", "create_schematic"]
