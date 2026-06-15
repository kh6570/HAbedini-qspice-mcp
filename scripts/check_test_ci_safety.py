#!/usr/bin/env python3
"""Guardrails for tests that pass locally but fail on clean CI checkouts.

Checks ``tests/`` for:
- references to the gitignored repo ``tmp/`` tree (fixture deps absent in CI)
- unconditional module-level ``pytest.skip(..., allow_module_level=True)``
- imports from other test modules via ``tests.unit`` / ``tests.integration``
  (use ``tests.support`` helpers instead)
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

EXCLUDE_DIRS = frozenset({"__pycache__", ".pytest_cache"})

GITIGNORED_TMP_REF = re.compile(
    r"""
    /\s*["']tmp["']\s*/     # / "tmp" /
    |["']tmp/                # "tmp/..."
    |["']tmp\\               # "tmp\\..." on Windows-style strings
    """,
    re.VERBOSE,
)

MODULE_LEVEL_SKIP = re.compile(
    r"^\s*pytest\.skip\s*\([^)]*allow_module_level\s*=\s*True",
    re.MULTILINE,
)

CROSS_TEST_MODULE_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+tests\.(?:unit|integration)\.",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    rule: str
    detail: str


def _scan_file(path: Path, *, root: Path) -> list[Violation]:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(root)
    violations: list[Violation] = []

    for pattern, rule, hint in (
        (GITIGNORED_TMP_REF, "gitignored-tmp-ref", "use tests/fixtures/ or tests/support/"),
        (
            MODULE_LEVEL_SKIP,
            "module-level-skip",
            "remove allow_module_level skip or fix the root cause",
        ),
        (
            CROSS_TEST_MODULE_IMPORT,
            "cross-test-import",
            "move shared bytes/helpers to tests/support/ instead of importing test modules",
        ),
    ):
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            snippet = match.group(0).strip()
            violations.append(
                Violation(
                    path=rel,
                    line=line,
                    rule=rule,
                    detail=f"{snippet} ({hint})",
                )
            )

    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    tests_root = root / "tests"
    if not tests_root.is_dir():
        print("ERROR: tests/ directory not found.", file=sys.stderr)
        return 1

    violations: list[Violation] = []
    for py_file in sorted(tests_root.rglob("*.py")):
        if any(part in EXCLUDE_DIRS for part in py_file.parts):
            continue
        violations.extend(_scan_file(py_file, root=root))

    if violations:
        print(f"ERROR: Found {len(violations)} test CI-safety violation(s):", file=sys.stderr)
        for item in violations:
            print(f"  - {item.path}:{item.line} [{item.rule}] {item.detail}", file=sys.stderr)
        return 1

    print("OK: No gitignored tmp/ deps, module-level skips, or cross-test imports in tests/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
