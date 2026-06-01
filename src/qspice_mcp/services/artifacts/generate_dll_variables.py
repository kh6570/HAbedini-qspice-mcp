"""Service for QUX-backed `.DLL` variable export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.artifacts._qux_export import (
    DllVariableExport,
    generate_dll_variables_with_qux,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

SERVICE_SPEC = ServiceSpec(
    name="generate_dll_variables",
    title="Generate DLL Variables",
    summary=("Generate `.DLL` variable declarations through the documented QUX companion command."),
    phase="implemented",
    read_only=False,
)


def generate_dll_variables(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    output_path: str | Path | None = None,
) -> DllVariableExport:
    """Generate `.DLL` variable declarations through `QUX.exe -DLLvariables`."""

    return generate_dll_variables_with_qux(
        schematic_path,
        workspace_root=workspace_root,
        settings=settings,
        output_path=output_path,
    )


__all__ = ["SERVICE_SPEC", "DllVariableExport", "generate_dll_variables"]
