#!/usr/bin/env python3
"""Guard MCP service contract prose against stale all-caps QSPICE tokens."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

MCP_CONTRACTS_DIR = Path("src/qspice_mcp/services")

# Standalone QSPICE prose, not QSPICE64* or QSPICE_* env/path tokens.
_STALE_PROSE = re.compile(r"\bQSPICE(?!64|_)")


@dataclass(frozen=True, slots=True)
class CasingIssue:
    path: Path
    line: int
    snippet: str


def collect_casing_issues(*, root: Path) -> list[CasingIssue]:
    contracts_root = root / MCP_CONTRACTS_DIR
    if not contracts_root.is_dir():
        return [CasingIssue(MCP_CONTRACTS_DIR, 0, "directory missing")]

    issues: list[CasingIssue] = []
    for path in sorted(contracts_root.rglob("mcp_contracts.py")):
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
            f"ERROR: Found {len(issues)} stale QSPICE prose token(s) in MCP contracts:",
            file=sys.stderr,
        )
        for item in issues:
            print(f"  - {item.path}:{item.line} {item.snippet}", file=sys.stderr)
        return 1

    print("OK: MCP service contracts use QSpice prose casing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
