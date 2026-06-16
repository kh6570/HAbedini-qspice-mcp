"""Service describing the optional live GUI orchestration surface."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class LiveGuiSupport:
    """Reported state of the optional live GUI orchestration layer."""

    windows_only: bool
    platform_supported: bool
    version_gated: bool
    external_bridge_required: bool
    session_manifest_scaffolding: bool
    qspice_executable_configured: bool
    runtime_session_management: bool = False
    bridge_command_configured: bool = False
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="describe_live_gui_support",
    title="Describe Live GUI Support",
    summary=(
        "Describe the optional Windows-only live GUI layer, including its version gate "
        "and external-bridge requirement."
    ),
    phase="implemented",
)


def describe_live_gui_support(*, settings: QSpiceSettings) -> LiveGuiSupport:
    """Describe the currently supported live GUI orchestration surface."""

    effective_settings = settings.normalized()
    platform_supported = sys.platform == "win32"
    bridge_command_configured = bool(effective_settings.live_gui_bridge_command)
    qspice_executable_configured = (
        effective_settings.exe is not None and effective_settings.exe.is_file()
    )

    notes = [
        "The live GUI layer is intentionally Windows-only and version-gated.",
        (
            "The repo manages manifest scaffolding plus bridge lifecycle launch, "
            "but the actual Windows-message bridge executable remains an external dependency."
        ),
        (
            "scaffold_live_gui_session can generate a manifest contract, and "
            "launch_live_gui_session can execute that contract through a configured bridge command."
        ),
    ]
    if not platform_supported:
        notes.append(
            "The current host platform is not Windows, so live GUI execution stays unavailable."
        )
    if not bridge_command_configured:
        notes.append(
            "No live GUI bridge command is configured, so runtime launch stays unavailable."
        )
    if not qspice_executable_configured:
        notes.append(
            "No configured QSpice executable is currently available for launch-command scaffolding."
        )

    return LiveGuiSupport(
        windows_only=True,
        platform_supported=platform_supported,
        version_gated=True,
        external_bridge_required=True,
        session_manifest_scaffolding=True,
        qspice_executable_configured=qspice_executable_configured,
        runtime_session_management=True,
        bridge_command_configured=bridge_command_configured,
        notes=tuple(notes),
    )


__all__ = ["SERVICE_SPEC", "LiveGuiSupport", "describe_live_gui_support"]
