"""Package entry point."""

from __future__ import annotations

import argparse
import json
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


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Each setting-bearing flag mirrors a ``QSPICE_*`` environment variable
    (``QSPICE_`` + the matching :class:`~qspice_mcp.infra.config.QSpiceSettings`
    field, upper-cased); the CLI value wins. The mapping is documented in
    ``docs/user-guide.md`` and enforced by ``tests/unit/test_cli_env_alias_mapping.py``.
    """

    parser = argparse.ArgumentParser(description="QSpice MCP server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"qspice-mcp {version('qspice-mcp')}",
    )
    parser.add_argument("--transport", choices=("stdio", "sse"), default=None)
    parser.add_argument("--qspice-exe", type=Path, default=None)
    parser.add_argument("--workspace-root", type=Path, default=None)
    parser.add_argument("--log-folder", type=Path, default=None)
    parser.add_argument("--recipe-path", type=Path, default=None)
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
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Print an environment readiness report as JSON and exit.",
    )
    return parser


def main() -> None:
    """Parse CLI arguments and run the MCP server."""
    parser = build_arg_parser()
    args = parser.parse_args()
    _configure_stdio_utf8()
    settings = build_settings(
        transport=args.transport,
        exe=args.qspice_exe,
        workspace_root=args.workspace_root,
        log_level=args.log_level,
        log_folder=args.log_folder,
        recipe_path=args.recipe_path,
    )
    configure_logging(settings.log_level, log_folder=settings.log_folder)

    if args.setup:
        from qspice_mcp.infra.bootstrap import describe_environment_readiness  # noqa: PLC0415

        print(json.dumps(describe_environment_readiness(settings), indent=2))
        raise SystemExit(0)

    if settings.transport == "sse" and not settings.enable_sse:
        print(
            "ERROR: the sse transport is gated behind QSPICE_ENABLE_SSE=true. "
            "Set the environment variable to opt in to the experimental SSE transport.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    raise SystemExit(run(settings=settings, describe=args.describe))


if __name__ == "__main__":
    main()
