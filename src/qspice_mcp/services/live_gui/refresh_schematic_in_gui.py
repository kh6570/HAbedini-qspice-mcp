"""Refresh one schematic view in the local GUI on Windows hosts."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING, Literal

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings

RefreshStrategy = Literal["reopen_via_association", "restart_qspice_and_reopen"]


@dataclass(frozen=True, slots=True)
class RefreshedSchematicInGui:
    """Metadata returned after requesting one GUI refresh workflow."""

    schematic_path: Path
    strategy: RefreshStrategy
    started: bool
    qspice_process_restart_requested: bool
    qspice_process_restart_exit_code: int | None
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="refresh_schematic_in_gui",
    title="Refresh Schematic In GUI",
    summary=(
        "Refresh one workspace-local .qsch view on Windows by reopening via OS association "
        "or by force-restarting QSpice before reopening."
    ),
    phase="implemented",
    read_only=False,
)


def refresh_schematic_in_gui(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    strategy: RefreshStrategy = "reopen_via_association",
    force_restart: bool = False,
) -> RefreshedSchematicInGui:
    """Run one local GUI refresh workflow for a workspace-local schematic."""

    if sys.platform != "win32":
        raise BackendUnavailableError(
            "refresh_schematic_in_gui is only available on Windows hosts."
        )

    resolved_path = validate_existing_file(
        schematic_path,
        workspace_root=workspace_root,
        suffixes=(".qsch",),
    )
    startfile = getattr(os, "startfile", None)
    if startfile is None:
        raise BackendUnavailableError(
            "The current Python runtime does not expose os.startfile for GUI launch."
        )

    restart_requested = strategy == "restart_qspice_and_reopen"
    restart_exit_code: int | None = None
    notes: list[str] = []

    if restart_requested:
        if not force_restart:
            raise ValidationError(
                "restart_qspice_and_reopen requires force_restart=true because it can close all open QSpice windows."  # noqa: E501
            )
        effective_settings = settings.normalized()
        qspice_process_name = (
            effective_settings.exe.name if effective_settings.exe is not None else "QSPICE64.exe"
        )
        taskkill = subprocess.run(  # noqa: S603
            ["taskkill", "/F", "/IM", qspice_process_name],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
        )
        restart_exit_code = taskkill.returncode
        if taskkill.returncode == 0:
            notes.append(
                f"Requested force-restart for process image {qspice_process_name} before reopening."
            )
        else:
            notes.append(
                f"taskkill returned exit code {taskkill.returncode} for process image {qspice_process_name}; proceeding with reopen."  # noqa: E501
            )
    else:
        notes.append(
            "Requested reopen via OS file association without force-restarting QSpice processes."
        )

    startfile(str(resolved_path))
    notes.append("Dispatched a schematic open request through the host OS file association.")

    return RefreshedSchematicInGui(
        schematic_path=resolved_path,
        strategy=strategy,
        started=True,
        qspice_process_restart_requested=restart_requested,
        qspice_process_restart_exit_code=restart_exit_code,
        notes=tuple(notes),
    )


__all__ = ["SERVICE_SPEC", "RefreshedSchematicInGui", "refresh_schematic_in_gui"]
