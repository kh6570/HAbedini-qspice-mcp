#!/usr/bin/env python3
"""Verify zero third-party imports (spicelib, qspice) in source and tests.

Exits with code 0 when clean, code 1 when forbidden imports are found.
"""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(spicelib|qspice)\b",
    re.MULTILINE,
)
EXCLUDE_DIRS = {"__pycache__", ".nox", ".venv", ".git", ".mypy_cache", ".pytest_cache"}
SCAN_DIRS = ("src", "tests", "scripts")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    violations: list[str] = []

    for directory in SCAN_DIRS:
        dir_path = root / directory
        if not dir_path.is_dir():
            continue
        for py_file in dir_path.rglob("*.py"):
            if any(part in EXCLUDE_DIRS for part in py_file.parts):
                continue
            text = py_file.read_text(encoding="utf-8")
            for match in FORBIDDEN.finditer(text):
                violations.append(f"{py_file.relative_to(root)}: {match.group(0).strip()}")

    if violations:
        print(f"ERROR: Found {len(violations)} forbidden third-party import(s):")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("OK: No forbidden third-party imports detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
