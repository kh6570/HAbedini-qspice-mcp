"""Service for renaming one component reference in a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor_backend import (
    _load_qsch_support_modules,
)
from qspice_mcp.services._backends.schematic_editor_edits import _component_symbol_tag
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RenamedComponentReference:
    """Metadata for one component reference rename."""

    schematic_path: Path
    output_path: Path
    reference: str
    new_reference: str


SERVICE_SPEC = ServiceSpec(
    name="rename_component_reference",
    title="Rename Component Reference",
    summary=(
        "Rename one schematic component reference, updating both the component "
        "and its embedded symbol text."
    ),
    phase="implemented",
    read_only=False,
)


def rename_component_reference(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    new_reference: str,
    output_path: str | Path | None = None,
) -> RenamedComponentReference:
    """Rename one component reference and persist the edited schematic."""

    normalized_new = new_reference.strip()
    if not normalized_new:
        raise ValueError("new_reference must not be empty.")

    def apply_rename(editor: object) -> None:
        editor_obj = cast("Any", editor)

        existing = {str(r) for r in editor_obj.get_components("*")}
        if normalized_new.upper() in {r.upper() for r in existing}:
            raise ValueError(f"Component reference already exists in schematic: {normalized_new}")

        # Update symbol text REFDES
        qsch_module, _ = _load_qsch_support_modules()
        _, symbol_tag = _component_symbol_tag(editor_obj, reference=reference)
        texts = cast("list[Any]", symbol_tag.get_items("text"))
        texts[qsch_module.QSCH_SYMBOL_TEXT_REFDES].set_attr(
            qsch_module.QSCH_TEXT_STR_ATTR, normalized_new
        )

        # Update component object reference
        component = editor_obj.get_component(reference)
        component.reference = normalized_new

        # Update internal components dictionary so the editor tracks under the new key
        components_dict = getattr(editor_obj, "components", None)
        if isinstance(components_dict, dict) and reference in components_dict:
            components_dict[normalized_new] = components_dict.pop(reference)

        editor_obj.updated = True

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_rename,
    )
    return RenamedComponentReference(
        schematic_path=resolved_path,
        output_path=saved_path,
        reference=reference,
        new_reference=normalized_new,
    )


__all__ = [
    "SERVICE_SPEC",
    "RenamedComponentReference",
    "rename_component_reference",
]
