"""Append one include or library directive to a netlist artifact."""

from __future__ import annotations

from dataclasses import dataclass
from shutil import copy2
from typing import TYPE_CHECKING, Literal

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._analysis_directive import (
    append_lines_before_end,
    resolve_staged_output_path,
)
from qspice_mcp.services.simulation._netlist_includes import (
    parse_netlist_directives,
    strip_quoted_include_token,
)

if TYPE_CHECKING:
    from pathlib import Path

IncludeKind = Literal["include", "inc", "lib"]
_NETLIST_SUFFIXES = (".net", ".cir", ".inc")
_LIBRARY_SUFFIXES = (".lib", ".inc", ".cir", ".net")


@dataclass(frozen=True, slots=True)
class LibraryIncludeAdd:
    """Metadata for one appended include directive."""

    source_netlist: Path
    output_netlist: Path
    include_path: Path
    directive: str
    already_present: bool


SERVICE_SPEC = ServiceSpec(
    name="add_library_include",
    title="Add Library Include",
    summary="Append one `.include`, `.inc`, or `.lib` directive to a netlist artifact.",
    phase="implemented",
    read_only=False,
)


def _format_include_path(
    include_path: Path,
    *,
    netlist_dir: Path,
    relative_to_netlist: bool,
) -> str:
    if relative_to_netlist:
        try:
            return include_path.resolve(strict=False).relative_to(netlist_dir).as_posix()
        except ValueError:
            return include_path.resolve(strict=False).as_posix()
    return include_path.resolve(strict=False).as_posix()


def _directive_already_present(
    netlist_path: Path,
    *,
    kind: IncludeKind,
    include_token: str,
) -> bool:
    normalized_token = include_token.strip().strip("'\"")
    for parsed_kind, _, raw_path in parse_netlist_directives(netlist_path):
        if parsed_kind != kind:
            continue
        if strip_quoted_include_token(raw_path) == normalized_token:
            return True
    return False


def add_library_include(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
    include_path: str | Path,
    kind: IncludeKind = "include",
    output_path: str | Path | None = None,
    relative_to_netlist: bool = True,
) -> LibraryIncludeAdd:
    """Append one include/library directive before the netlist ``.end`` marker."""

    normalized_workspace = workspace_root.resolve(strict=False)
    source_netlist = validate_existing_file(
        netlist_path,
        workspace_root=normalized_workspace,
        suffixes=_NETLIST_SUFFIXES,
    )
    resolved_include = validate_existing_file(
        include_path,
        workspace_root=normalized_workspace,
        suffixes=_LIBRARY_SUFFIXES,
    )
    destination = resolve_staged_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=source_netlist,
        allowed_suffixes=_NETLIST_SUFFIXES,
    )
    if destination != source_netlist:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(source_netlist, destination)

    include_token = _format_include_path(
        resolved_include,
        netlist_dir=destination.parent,
        relative_to_netlist=relative_to_netlist,
    )
    directive = f".{kind} {include_token}"
    already_present = _directive_already_present(
        destination,
        kind=kind,
        include_token=include_token,
    )
    if already_present:
        raise ValidationError(f"Include directive already present: {directive}")

    append_lines_before_end(destination, (directive,))
    return LibraryIncludeAdd(
        source_netlist=source_netlist,
        output_netlist=destination,
        include_path=resolved_include,
        directive=directive,
        already_present=False,
    )


__all__ = ["SERVICE_SPEC", "IncludeKind", "LibraryIncludeAdd", "add_library_include"]
