#!/usr/bin/env python3
"""Guard MCP tool metadata against stale all-caps QSPICE prose.

Public docs and tool descriptions use the Qorvo-style product name ``QSpice``.
Identifiers such as ``QSPICE_EXE``, ``QSPICE64.exe``, and install paths under
``Program Files\\QSPICE\\`` must stay untouched.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

TOOL_METADATA_DIR = Path("src/qspice_mcp/mcp/_tool_metadata")

# Standalone QSPICE prose, not QSPICE64* or QSPICE_* env/path tokens.
_STALE_PROSE = re.compile(r"\bQSPICE(?!64|_)")


@dataclass(frozen=True, slots=True)
class CasingIssue:
    path: Path
    line: int
    snippet: str


def collect_casing_issues(*, root: Path) -> list[CasingIssue]:
    metadata_root = root / TOOL_METADATA_DIR
    if not metadata_root.is_dir():
        return [CasingIssue(TOOL_METADATA_DIR, 0, "directory missing")]

    issues: list[CasingIssue] = []
    for path in sorted(metadata_root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = _STALE_PROSE.search(line)
            if match is not None:
                issues.append(
                    CasingIssue(
                        path=path.relative_to(root),
                        line=lineno,
                        snippet=line.strip(),
                    )
                )
    return issues


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    issues = collect_casing_issues(root=root)
    if issues:
        print(
            f"ERROR: Found {len(issues)} stale QSPICE prose token(s) in tool metadata:",
            file=sys.stderr,
        )
        for item in issues:
            print(f"  - {item.path}:{item.line} {item.snippet}", file=sys.stderr)
        return 1

    print("OK: MCP tool metadata uses QSpice prose casing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
