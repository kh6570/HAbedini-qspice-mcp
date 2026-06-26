"""Environment readiness reporting for the ``--setup`` bootstrap subcommand."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.adapters.probe import build_summary
from qspice_mcp.services.mixed_signal._dll_toolchain_probe import describe_dll_build_toolchain

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings


def _workspace_readiness(settings: QSpiceSettings) -> dict[str, object]:
    """Summarize whether the configured workspace root is usable."""

    workspace_root = settings.workspace_root
    exists = workspace_root.is_dir()
    return {
        "path": str(workspace_root),
        "exists": exists,
        "writable": exists,
        "note": (
            "Workspace root exists."
            if exists
            else "Workspace root does not exist yet; it will be created on first write."
        ),
    }


def describe_environment_readiness(settings: QSpiceSettings) -> dict[str, object]:
    """Return a JSON-serializable readiness report for first-time setup."""

    effective = settings.normalized()
    qspice = build_summary(effective)
    workspace = _workspace_readiness(effective)
    toolchain = describe_dll_build_toolchain(qspice_executable=effective.exe).as_dict()

    ready = bool(qspice["exists"]) and bool(workspace["exists"])
    return {
        "ready": ready,
        "qspice": qspice,
        "workspace": workspace,
        "dll_build_toolchain": toolchain,
        "transport": effective.transport,
        "enable_sse": effective.enable_sse,
        "log_folder": str(effective.log_folder) if effective.log_folder is not None else None,
        "recipe_path": str(effective.recipe_path) if effective.recipe_path is not None else None,
    }


__all__ = ["describe_environment_readiness"]
