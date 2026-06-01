"""Skeleton fixture capture utility for QSpice schematic examples."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def iter_schematics(repo_root: Path) -> list[Path]:
    """Return bundled recipe schematic files in a stable order."""
    recipes_dir = repo_root / "src" / "qspice_mcp" / "data" / "recipes"
    return sorted(recipes_dir.glob("*/Buck-converter.qsch"))


def main() -> int:
    """List planned fixture capture work or exit until execution is implemented."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="List planned work only")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    fixtures_dir = repo_root / "tests" / "fixtures" / "qraw"
    schematics = iter_schematics(repo_root)
    executable = os.getenv("QSPICE_EXE", "<unset>")

    print(f"QSPICE_EXE={executable}")
    print(f"Fixtures dir: {fixtures_dir}")
    for schematic in schematics:
        print(
            f"Would capture from schematic: {schematic.name} -> "
            f"{schematic.stem}.qraw / {schematic.stem}.log"
        )

    if args.dry_run:
        return 0

    print("Schematic execution is not implemented yet. Use --dry-run for now.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
