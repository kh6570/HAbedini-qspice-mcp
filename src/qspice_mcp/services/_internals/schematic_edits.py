"""Shared helpers for QschEditor-backed schematic mutation services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    open_schematic_editor,
    resolve_schematic_output_path,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from qspice_mcp.services._backends.schematic_editor import _QschEditorProtocol


def save_editor_as(
    editor: _QschEditorProtocol,
    *,
    workspace_root: Path,
    output_path: str | Path | None,
    default: Path,
) -> Path:
    """Persist an editor-like object to a resolved schematic path."""

    destination = resolve_schematic_output_path(
        output_path,
        workspace_root=workspace_root.resolve(strict=False),
        default=default,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    editor.save_as(destination)
    return destination.resolve(strict=False)


def save_edited_schematic(
    editor: _QschEditorProtocol,
    *,
    schematic_path: Path,
    workspace_root: Path,
    output_path: str | Path | None,
) -> Path:
    """Persist one edited schematic to the requested destination."""

    return save_editor_as(
        editor,
        workspace_root=workspace_root,
        output_path=output_path,
        default=schematic_path,
    )


def edit_schematic(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    apply_edit: Callable[[_QschEditorProtocol], None] | None = None,
) -> tuple[Path, Path]:
    """Open a schematic, optionally apply an edit, persist, return (resolved, saved)."""

    editor, resolved_path, _ = open_schematic_editor(
        schematic_path, workspace_root=workspace_root.resolve(strict=False)
    )
    if apply_edit is not None:
        apply_edit(editor)
    saved_path = save_edited_schematic(
        editor,
        schematic_path=resolved_path,
        workspace_root=workspace_root,
        output_path=output_path,
    )
    return resolved_path, saved_path


__all__ = ["edit_schematic", "save_edited_schematic", "save_editor_as"]
