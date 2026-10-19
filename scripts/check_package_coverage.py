# In the name of God, the Most Gracious, the Most Merciful
"""Enforce per-package coverage floors using existing coverage data."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoverageFloor:
    label: str
    include_pattern: str
    minimum_pct: int


PACKAGE_FLOORS: tuple[CoverageFloor, ...] = (
    CoverageFloor("adapters", "src/qspice_mcp/adapters/*", 80),
    CoverageFloor("core", "src/qspice_mcp/core/*", 72),
    # Linux cannot execute the Windows process branches, so this floor is 84 there.
    CoverageFloor("infra", "src/qspice_mcp/infra/*", 84),
    CoverageFloor("mcp", "src/qspice_mcp/mcp/*", 80),
    CoverageFloor("services", "src/qspice_mcp/services/*", 78),
)


def main() -> int:
    for floor in PACKAGE_FLOORS:
        print(f"\n=== Coverage floor: {floor.label} >= {floor.minimum_pct}% ===")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "report",
                f"--include={floor.include_pattern}",
                f"--fail-under={floor.minimum_pct}",
            ],
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
