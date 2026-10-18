# In the name of God, the Most Gracious, the Most Merciful
"""Service discovery for QSpice. The walker lives in mcp-app-core."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from mcp_app_core.catalog import ServiceSpec, enrich_spec
from mcp_app_core.catalog import discover_package_specs as _discover_package_specs
from mcp_app_core.catalog import load_contracts as _load_contracts
from mcp_app_core.catalog import resolve_service_module as _resolve_service_module

if TYPE_CHECKING:
    from types import ModuleType

_SERVICE_PACKAGE_ORDER: tuple[str, ...] = (
    "schematic",
    "subcircuit",
    "simulation",
    "batch",
    "remote",
    "waveform",
    "artifacts",
    "mixed_signal",
    "protocol",
    "live_gui",
    "workspace",
    "instructions",
    "recipes",
    "topology",
)
_PACKAGES = tuple(f"qspice_mcp.services.{name}" for name in _SERVICE_PACKAGE_ORDER)


def discover_package_mcp_contracts(package_name: str) -> dict[str, dict[str, object]]:
    """Return MCP contract rows declared under one service package."""

    return _load_contracts(f"qspice_mcp.services.{package_name}")


@cache
def build_mcp_contract_catalog() -> dict[str, dict[str, object]]:
    """Build the full MCP contract catalog from service packages and internals."""

    catalog: dict[str, dict[str, object]] = {}
    for package_name in _PACKAGES:
        catalog.update(_load_contracts(package_name))
    internals = _load_contracts("qspice_mcp.services._internals")
    catalog.update(internals)
    return catalog


@cache
def discover_package_service_specs(package_name: str) -> tuple[ServiceSpec, ...]:
    """Return all SERVICE_SPEC definitions found under a service package."""

    return _discover_package_specs(f"qspice_mcp.services.{package_name}")


@cache
def build_service_spec_catalog(
    extra_specs: tuple[ServiceSpec, ...] = (),
) -> tuple[ServiceSpec, ...]:
    """Build the full service catalog from discovered package service specs."""

    contracts = build_mcp_contract_catalog()
    catalog = [enrich_spec(spec, contracts.get(spec.name)) for spec in extra_specs]
    for package_name in _PACKAGES:
        catalog.extend(_discover_package_specs(package_name))
    return tuple(catalog)


def resolve_service_module(service_name: str) -> ModuleType:
    """Import and return the service module for one catalog tool name."""

    return _resolve_service_module(_PACKAGES, service_name)


@cache
def build_service_callable_catalog() -> dict[str, object]:
    """Map implemented tool names to their primary service callables."""

    catalog: dict[str, object] = {}
    for spec in build_service_spec_catalog():
        if spec.phase != "implemented":
            continue
        module = resolve_service_module(spec.name)
        service_fn = getattr(module, spec.name, None)
        if callable(service_fn):
            catalog[spec.name] = service_fn
    return catalog


__all__ = [
    "build_mcp_contract_catalog",
    "build_service_callable_catalog",
    "build_service_spec_catalog",
    "discover_package_mcp_contracts",
    "discover_package_service_specs",
    "resolve_service_module",
]
