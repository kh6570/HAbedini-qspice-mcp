"""Open one schematic in the local GUI through the host OS association."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import Literal

from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec


@dataclass(frozen=True, slots=True)
class OpenedSchematicInGui:
    """Metadata returned after requesting a local GUI open action."""

    schematic_path: Path
    launcher: Literal["os_file_association"]
    started: bool
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="open_schematic_in_gui",
    title="Open Schematic In GUI",
    summary=(
        "Open one .qsch file through the local Windows OS file association as a "
        "host-side convenience action."
    ),
    phase="implemented",
    read_only=False,
)


def open_schematic_in_gui(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
) -> OpenedSchematicInGui:
    """Open one workspace-local schematic in the desktop GUI on Windows."""

    if sys.platform != "win32":
        raise BackendUnavailableError("open_schematic_in_gui is only available on Windows hosts.")

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

    startfile(str(resolved_path))
    return OpenedSchematicInGui(
        schematic_path=resolved_path,
        launcher="os_file_association",
        started=True,
        notes=(
            "Opened the schematic through the host OS file association.",
            "This convenience action does not provide live GUI automation or refresh guarantees.",
        ),
    )


__all__ = ["SERVICE_SPEC", "OpenedSchematicInGui", "open_schematic_in_gui"]
