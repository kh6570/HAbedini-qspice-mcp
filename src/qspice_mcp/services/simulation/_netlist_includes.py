"""Parse and resolve `.include`/`.lib` directives referenced by netlists."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

_NETLIST_SUFFIXES = (".net", ".cir", ".inc")
_INCLUDE_LINE = re.compile(
    r"^\s*\.(?P<kind>include|inc|lib)\s+(?P<path>.+?)\s*(?:;.*)?$",
    re.IGNORECASE,
)
_MAX_INCLUDE_DEPTH = 8
_MIN_QUOTED_TOKEN_LENGTH = 2


@dataclass(frozen=True, slots=True)
class NetlistInclude:
    """One include or library reference discovered in a netlist graph."""

    kind: str
    directive: str
    raw_path: str
    resolved_path: Path | None
    exists: bool
    source_netlist: Path


def _strip_quotes(token: str) -> str:
    stripped = token.strip()
    if (
        len(stripped) >= _MIN_QUOTED_TOKEN_LENGTH
        and stripped[0] == stripped[-1]
        and stripped[0] in {"'", '"'}
    ):
        return stripped[1:-1]
    return stripped


def _resolve_include_path(
    raw_path: str,
    *,
    base_dir: Path,
    workspace_root: Path,
) -> Path | None:
    candidate = _strip_quotes(raw_path)
    if not candidate:
        return None
    relative = (base_dir / candidate).resolve(strict=False)
    if relative.is_file():
        return relative
    try:
        return resolve_workspace_path(candidate, workspace_root=workspace_root)
    except ValueError:
        return relative if relative.is_file() else None


def _parse_directives(netlist_path: Path) -> tuple[tuple[str, str, str], ...]:
    text = netlist_path.read_text(encoding="utf-8", errors="replace")
    directives: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        match = _INCLUDE_LINE.match(line)
        if match is None:
            continue
        kind = match.group("kind").lower()
        raw_path = match.group("path").strip()
        directive = f".{kind}"
        directives.append((kind, directive, raw_path))
    return tuple(directives)


def collect_netlist_includes(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
    max_depth: int = _MAX_INCLUDE_DEPTH,
) -> tuple[NetlistInclude, ...]:
    """Collect include/library directives reachable from one netlist root."""

    normalized_workspace = workspace_root.resolve(strict=False)
    root = validate_existing_file(
        netlist_path,
        workspace_root=normalized_workspace,
        suffixes=_NETLIST_SUFFIXES,
    )
    discovered: list[NetlistInclude] = []
    seen_resolved: set[Path] = set()
    queue: list[tuple[Path, int]] = [(root, 0)]

    while queue:
        current, depth = queue.pop(0)
        if depth > max_depth:
            continue
        for kind, directive, raw_path in _parse_directives(current):
            resolved = _resolve_include_path(
                raw_path,
                base_dir=current.parent,
                workspace_root=normalized_workspace,
            )
            exists = resolved is not None and resolved.is_file()
            discovered.append(
                NetlistInclude(
                    kind=kind,
                    directive=directive,
                    raw_path=raw_path,
                    resolved_path=resolved,
                    exists=exists,
                    source_netlist=current,
                )
            )
            if exists and resolved is not None and resolved.suffix.lower() in _NETLIST_SUFFIXES:
                if resolved in seen_resolved:
                    continue
                seen_resolved.add(resolved)
                queue.append((resolved, depth + 1))

    return tuple(discovered)


def hash_include_dependencies(
    includes: Iterable[NetlistInclude],
) -> tuple[tuple[str, str, float], ...]:
    """Return stable content hashes for existing include files."""

    hashed: list[tuple[str, str, float]] = []
    for include in includes:
        if not include.exists or include.resolved_path is None:
            continue
        resolved = include.resolved_path.resolve(strict=False)
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
        hashed.append((str(resolved), digest, resolved.stat().st_mtime))
    return tuple(sorted(hashed))


__all__ = [
    "NetlistInclude",
    "collect_netlist_includes",
    "hash_include_dependencies",
]
