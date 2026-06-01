"""Bootstrap check for the configured QSpice executable."""

from __future__ import annotations

import argparse
import json

from qspice_mcp.adapters.probe import build_summary


def main() -> int:
    """Run the bootstrap executable check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    summary = build_summary()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"Configured: {summary['configured']}")
        print(f"Executable: {summary['executable']}")
        print(f"Exists: {summary['exists']}")
        print(summary["note"])

    return 0 if summary["exists"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
