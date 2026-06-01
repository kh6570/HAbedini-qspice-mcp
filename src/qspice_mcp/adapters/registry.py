"""Adapter registration and selection."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from qspice_mcp.core.exceptions import AdapterNotFoundError

from .cli.qspice_v1 import CurrentQSpiceCLIAdapter
from .probe import ProbeResult, probe_qspice

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings

    from .base import AdapterDescription, QSpiceAdapter

_REGISTERED_ADAPTERS: tuple[QSpiceAdapter, ...] = (
    cast("QSpiceAdapter", CurrentQSpiceCLIAdapter()),
)


def get_registered_adapters() -> tuple[QSpiceAdapter, ...]:
    """Return registered QSpice adapters in selection order."""

    return _REGISTERED_ADAPTERS


def describe_adapters(
    probe: ProbeResult | None = None,
    *,
    settings: QSpiceSettings | None = None,
) -> tuple[AdapterDescription, ...]:
    """Describe all registered adapters against the current probe result."""

    effective_probe = probe or probe_qspice(settings)
    return tuple(adapter.describe(effective_probe) for adapter in _REGISTERED_ADAPTERS)


def select_adapter(
    probe: ProbeResult | None = None,
    *,
    settings: QSpiceSettings | None = None,
) -> QSpiceAdapter:
    """Select the first adapter that can handle the current executable."""

    effective_probe = probe or probe_qspice(settings)
    for adapter in _REGISTERED_ADAPTERS:
        if adapter.can_handle(effective_probe):
            return adapter
    raise AdapterNotFoundError("No registered adapter can handle the current QSpice executable.")
