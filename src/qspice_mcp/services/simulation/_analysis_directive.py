"""Shared helpers for staging analysis directives on schematics or netlists."""

from __future__ import annotations

from shutil import copy2
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.schematic.add_instruction import (
    add_instruction as add_instruction_service,
)

if TYPE_CHECKING:
    from pathlib import Path

_NETLIST_SUFFIXES = (".net", ".cir")
SourceKind = Literal["schematic", "netlist"]


def resolve_staged_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
    allowed_suffixes: tuple[str, ...],
) -> Path:
    if output_path is None:
        return default.resolve(strict=False)
    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() not in allowed_suffixes:
        rendered_suffixes = ", ".join(allowed_suffixes)
        raise ValueError(f"Output path must end in one of: {rendered_suffixes}")
    return resolved


def append_instruction_to_netlist(netlist_path: Path, instruction: str) -> None:
    append_lines_before_end(netlist_path, (instruction,))


def append_lines_before_end(netlist_path: Path, lines: tuple[str, ...]) -> None:
    """Insert one or more lines immediately before the trailing ``.end`` directive."""

    if not lines:
        return
    existing = netlist_path.read_text(encoding="utf-8", errors="replace")
    line_ending = "\r\n" if "\r\n" in existing else "\n"
    normalized_lines = existing.replace("\r\n", "\n").split("\n")
    if normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()

    end_index = len(normalized_lines)
    for index in range(len(normalized_lines) - 1, -1, -1):
        if normalized_lines[index].strip().lower() == ".end":
            end_index = index
            break

    for offset, line in enumerate(lines):
        normalized_lines.insert(end_index + offset, line)
    netlist_path.write_text(
        f"{line_ending.join(normalized_lines)}{line_ending}",
        encoding="utf-8",
    )


def stage_analysis_directive(
    source_path: str | Path,
    *,
    workspace_root: Path,
    instruction: str,
    default_stem_suffix: str,
    schematic_warning: str,
    netlist_warning: str,
    output_path: str | Path | None = None,
) -> tuple[Path, Path, SourceKind, str]:
    """Stage one analysis directive on a schematic copy or netlist artifact."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )

    if resolved_source.suffix.lower() == ".qsch":
        destination = resolve_staged_output_path(
            output_path,
            workspace_root=normalized_workspace,
            default=resolved_source.with_name(f"{resolved_source.stem}-{default_stem_suffix}.qsch"),
            allowed_suffixes=(".qsch",),
        )
        added = add_instruction_service(
            resolved_source,
            workspace_root=normalized_workspace,
            instruction=instruction,
            output_path=destination,
        )
        return resolved_source, added.output_path, "schematic", schematic_warning

    destination = resolve_staged_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=resolved_source.with_name(
            f"{resolved_source.stem}-{default_stem_suffix}{resolved_source.suffix}"
        ),
        allowed_suffixes=_NETLIST_SUFFIXES,
    )
    if destination != resolved_source:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(resolved_source, destination)
    append_instruction_to_netlist(destination, instruction)
    return resolved_source, destination, "netlist", netlist_warning


__all__ = [
    "_NETLIST_SUFFIXES",
    "append_instruction_to_netlist",
    "append_lines_before_end",
    "resolve_staged_output_path",
    "stage_analysis_directive",
]
