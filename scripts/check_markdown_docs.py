#!/usr/bin/env python3
"""Lightweight markdown doc lint for the public doc set.

Targets the two failure classes seen in the field without pulling in a Node
toolchain:

- **Broken relative links** — ``[text](path)`` / ``![alt](path)`` pointing at a
  workspace file that does not exist (anchors and ``http(s)``/``mailto`` URLs are
  ignored).
- **Malformed GFM tables** — pipe rows split from their header by a blank line
  (the doubled-blank-line bug that rendered AGENTS.md tables as one-row tables)
  and rows whose column count does not match the delimiter row.

Scans ``README.md``, ``AGENTS.md``, ``SECURITY.md``, ``CHANGELOG.md`` and
``docs/*.md``. Code fences and inline code spans are skipped.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT_DOCS = ("README.md", "AGENTS.md", "SECURITY.md", "CHANGELOG.md")
DOCS_GLOB = "docs/*.md"

_FENCE = re.compile(r"^\s*(```|~~~)")
_INLINE_CODE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+\"[^\"]*\")?\s*\)")
_DELIMITER = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?$")
_SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")


@dataclass(frozen=True, slots=True)
class DocIssue:
    path: Path
    line: int
    rule: str
    detail: str


def _cell_count(row: str) -> int:
    stripped = row.strip()
    inner = stripped.strip("|")
    return len(inner.split("|"))


def _is_pipe_row(line: str) -> bool:
    return line.strip().startswith("|")


def _check_links(rel: Path, lines: list[str], in_code: list[bool], *, root: Path) -> list[DocIssue]:
    issues: list[DocIssue] = []
    doc_dir = Path(rel).parent
    for idx, line in enumerate(lines):
        if in_code[idx]:
            continue
        cleaned = _INLINE_CODE.sub("", line)
        for match in _LINK.finditer(cleaned):
            target = match.group(1)
            if target.startswith(_SKIP_LINK_PREFIXES) or "://" in target:
                continue
            file_part = target.split("#", 1)[0]
            if not file_part:
                continue
            rel_target = (doc_dir / file_part).as_posix()
            if not (root / rel_target).exists():
                issues.append(
                    DocIssue(
                        path=rel,
                        line=idx + 1,
                        rule="broken-link",
                        detail=f"{target} -> {rel_target}",
                    )
                )
    return issues


def _check_tables(rel: Path, lines: list[str], in_code: list[bool]) -> list[DocIssue]:
    issues: list[DocIssue] = []
    in_table: list[bool] = [False] * len(lines)
    idx = 0
    while idx < len(lines):
        if (
            not in_code[idx]
            and _DELIMITER.match(lines[idx].strip())
            and "|" in lines[idx]
            and idx > 0
            and _is_pipe_row(lines[idx - 1])
            and not in_code[idx - 1]
        ):
            columns = _cell_count(lines[idx])
            in_table[idx - 1] = True
            in_table[idx] = True
            header_cells = _cell_count(lines[idx - 1])
            if header_cells != columns:
                issues.append(
                    DocIssue(
                        path=rel,
                        line=idx,
                        rule="table-column-mismatch",
                        detail=f"header has {header_cells} cells, delimiter {columns}",
                    )
                )
            body = idx + 1
            while body < len(lines) and not in_code[body] and _is_pipe_row(lines[body]):
                in_table[body] = True
                if _cell_count(lines[body]) != columns:
                    issues.append(
                        DocIssue(
                            path=rel,
                            line=body + 1,
                            rule="table-column-mismatch",
                            detail=f"row has {_cell_count(lines[body])} cells, expected {columns}",
                        )
                    )
                body += 1
            idx = body
            continue
        idx += 1

    for line_idx, line in enumerate(lines):
        if in_code[line_idx] or in_table[line_idx]:
            continue
        if _is_pipe_row(line) and not _DELIMITER.match(line.strip()):
            issues.append(
                DocIssue(
                    path=rel,
                    line=line_idx + 1,
                    rule="stray-table-row",
                    detail="pipe row not attached to a header+delimiter (blank line split?)",
                )
            )
    return issues


def _code_mask(lines: list[str]) -> list[bool]:
    mask: list[bool] = []
    in_fence = False
    for line in lines:
        if _FENCE.match(line):
            mask.append(True)
            in_fence = not in_fence
            continue
        mask.append(in_fence)
    return mask


def _scan_file(rel: Path, *, root: Path) -> list[DocIssue]:
    lines = (root / rel).read_text(encoding="utf-8").splitlines()
    in_code = _code_mask(lines)
    return _check_links(rel, lines, in_code, root=root) + _check_tables(rel, lines, in_code)


def _target_files(root: Path) -> list[Path]:
    targets = [Path(name) for name in ROOT_DOCS if (root / name).is_file()]
    targets.extend(sorted(p.relative_to(root) for p in (root / "docs").glob("*.md")))
    return targets


def collect_issues(*, root: Path) -> list[DocIssue]:
    issues: list[DocIssue] = []
    for rel in _target_files(root):
        issues.extend(_scan_file(rel, root=root))
    return issues


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    issues = collect_issues(root=root)
    if issues:
        print(f"ERROR: Found {len(issues)} markdown doc issue(s):", file=sys.stderr)
        for item in issues:
            print(f"  - {item.path}:{item.line} [{item.rule}] {item.detail}", file=sys.stderr)
        return 1

    print("OK: markdown docs have valid relative links and well-formed tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
