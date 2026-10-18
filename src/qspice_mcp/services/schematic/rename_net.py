# In the name of God, the Most Gracious, the Most Merciful
"""Rename explicit schematic net labels and wire names in one edit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._backends.schematic_editor_backend import (
    _normalize_net_name,
    _quote_qsch_string,
    _unquote_qsch_string,
)
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


@dataclass(frozen=True, slots=True)
class RenamedNet:
    """Names and counts of explicit net items changed by a rename."""

    schematic_path: Path
    output_path: Path
    net_name: str
    new_net_name: str
    labels_renamed: int
    wires_renamed: int


SERVICE_SPEC = ServiceSpec(
    name="rename_net",
    title="Rename Net",
    summary="Rename all matching net labels and explicit wire names in one schematic edit.",
    phase="implemented",
    read_only=False,
)


def rename_net(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    net_name: str,
    new_net_name: str,
    output_path: str | Path | None = None,
) -> RenamedNet:
    """Rename schematic net tags, rejecting ground renames and destination merges.

    Names match case-insensitively, as in SPICE. Text directives, expressions,
    component values, and embedded symbol pin names are not rewritten.
    """

    old_name = _normalize_net_name(net_name)
    new_name = _normalize_net_name(new_net_name)
    if old_name.casefold() == new_name.casefold():
        raise ValidationError("new_net_name must differ from net_name.")
    if {old_name.upper(), new_name.upper()} & {"0", "GND"}:
        raise ValidationError("Renaming to or from the ground net is not supported.")

    labels_renamed = 0
    wires_renamed = 0

    def apply_rename(editor: _QschEditorProtocol) -> None:
        nonlocal labels_renamed, wires_renamed
        if editor.schematic is None:
            raise ValidationError("Editor does not expose a root schematic tree.")
        matches = []
        schematic_tree = cast("Any", editor.schematic)
        for tag in schematic_tree.items:
            name_index = {"net": 5, "wire": 3}.get(tag.tag)
            if name_index is None or len(tag.tokens) <= name_index:
                continue
            name = _unquote_qsch_string(str(tag.tokens[name_index])).casefold()
            if name == new_name.casefold():
                raise ValidationError(
                    f"Net {new_name!r} already exists; refusing to merge distinct nets."
                )
            if name == old_name.casefold():
                matches.append((tag, name_index))
        if not matches:
            raise ValidationError(f"No net labels or named wires found for {old_name!r}.")
        for tag, name_index in matches:
            tag.tokens[name_index] = _quote_qsch_string(new_name)
            if tag.tag == "net":
                labels_renamed += 1
            else:
                wires_renamed += 1
        editor.updated = True

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_rename,
    )
    return RenamedNet(
        schematic_path=resolved_path,
        output_path=saved_path,
        net_name=old_name,
        new_net_name=new_name,
        labels_renamed=labels_renamed,
        wires_renamed=wires_renamed,
    )
