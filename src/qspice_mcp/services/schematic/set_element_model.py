"""Service for updating one component model in a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ElementModelUpdate:
    """Metadata for one component model edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    model: str


SERVICE_SPEC = ServiceSpec(
    name="set_element_model",
    title="Set Element Model",
    summary="Update the model text of one schematic component.",
    phase="implemented",
    read_only=False,
)


def set_element_model(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    model: str,
    output_path: str | Path | None = None,
) -> ElementModelUpdate:
    """Update one component model and persist the edited schematic."""

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=lambda editor: editor.set_element_model(reference, model),
    )
    return ElementModelUpdate(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        model=model,
    )


__all__ = ["SERVICE_SPEC", "ElementModelUpdate", "set_element_model"]
