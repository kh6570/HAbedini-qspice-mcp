"""Schematic edit helpers: structure."""

from __future__ import annotations

from typing import Any, cast

from qspice_mcp.core.exceptions import QSpiceError

from ..schematic_editor_backend import (
    _load_qsch_support_modules,
    _QschEditorProtocol,
)


def _append_schematic_tag(editor: _QschEditorProtocol, tag: object) -> None:
    """Append one raw QSch tag to the root schematic tree (idempotent)."""

    bootstrap_blank_schematic(editor)
    if editor.schematic is None:
        raise QSpiceError("Editor does not expose a root schematic tree.")
    schematic_obj: Any = editor.schematic
    items = cast("list[Any]", schematic_obj.items)
    if tag in items:
        return  # avoid double-append when add_component already registered it
    items.append(tag)
    editor.updated = True


def bootstrap_blank_schematic(editor: _QschEditorProtocol) -> None:
    """Attach a minimal root tag to an editor created with `create_blank=True`."""

    if editor.schematic is not None:
        return
    qsch_module, _ = _load_qsch_support_modules()
    editor.schematic = qsch_module.QschTag("schematic")
    editor.updated = True
