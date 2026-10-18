# In the name of God, the Most Gracious, the Most Merciful
"""Application services.

Import the concrete module you need. This package does not import every service
at startup; the tool registry discovers specs from the service packages.
"""

from __future__ import annotations

import sys
from importlib import import_module

from qspice_mcp.services.service_spec import ServiceSpec

_DESCRIBE_SERVER_CAPABILITIES_SERVICE = ServiceSpec(
    name="describe_server_capabilities",
    title="Describe Server Capabilities",
    summary="Report server-level backend availability, degraded tool groups, and feature flags.",
    phase="implemented",
)

_LEGACY_MODULE_ALIASES: dict[str, str] = {
    "_batch_manager": "qspice_mcp.services._internals.batch_manager",
    "_schematic_editor_backend": "qspice_mcp.services._backends.schematic_editor",
    "_schematic_edits": "qspice_mcp.services._internals.schematic_edits",
    "_simulation_batch": "qspice_mcp.services._internals.simulation_batch",
    "_step_filters": "qspice_mcp.services._internals.step_filters",
    "_waveform_backend": "qspice_mcp.services._backends.waveform",
}


def _register_legacy_module_aliases() -> None:
    for legacy_name, target in _LEGACY_MODULE_ALIASES.items():
        sys.modules.setdefault(f"{__name__}.{legacy_name}", import_module(target))


def get_service_specs() -> tuple[ServiceSpec, ...]:
    """Return the service catalog in registration order."""

    from qspice_mcp.services._internals.service_catalog import (  # noqa: PLC0415
        build_service_spec_catalog,
    )

    return build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))


_register_legacy_module_aliases()

__all__ = ["get_service_specs"]
