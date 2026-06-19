"""Package entry point."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from qspice_mcp.infra import build_settings, configure_logging
from qspice_mcp.mcp import run


def _configure_stdio_utf8() -> None:
    """Prefer UTF-8 stdio on Windows so tool output with Unicode does not crash."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue


def main() -> None:
    """Parse CLI arguments and run the MCP server."""
    parser = argparse.ArgumentParser(description="QSpice MCP server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"qspice-mcp {version('qspice-mcp')}",
    )
    parser.add_argument("--transport", choices=("stdio", "sse"), default="stdio")
    parser.add_argument("--qspice-exe", type=Path, default=None)
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument(
        "--log-level",
        choices=("debug", "info", "warning", "error"),
        default=None,
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Print the bootstrap summary as JSON and exit successfully.",
    )
    args = parser.parse_args()
    _configure_stdio_utf8()
    settings = build_settings(
        transport=args.transport,
        exe=args.qspice_exe,
        workspace_root=args.workspace_root,
        log_level=args.log_level,
    )
    configure_logging(settings.log_level)
    raise SystemExit(run(settings=settings, describe=args.describe))


if __name__ == "__main__":
    main()
