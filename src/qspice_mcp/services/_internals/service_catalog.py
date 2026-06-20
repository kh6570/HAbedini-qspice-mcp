"""Deterministic discovery helpers for the planned service catalog."""

from __future__ import annotations

from functools import cache
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType  # noqa: TC003

from qspice_mcp.services.service_spec import ServiceSpec

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
)


@cache
def discover_package_service_specs(package_name: str) -> tuple[ServiceSpec, ...]:
    """Return all ``SERVICE_SPEC`` definitions found under a service package."""

    package = import_module(f"qspice_mcp.services.{package_name}")
    package_path = getattr(package, "__path__", None)
    if package_path is None:
        raise TypeError(f"qspice_mcp.services.{package_name} is not a package.")

    specs: list[ServiceSpec] = []
    for module_info in sorted(iter_modules(package_path), key=lambda entry: entry.name):
        if module_info.name.startswith("_"):
            continue
        module = import_module(f"{package.__name__}.{module_info.name}")
        service_spec = getattr(module, "SERVICE_SPEC", None)
        if service_spec is None:
            continue
        if not isinstance(service_spec, ServiceSpec):
            raise TypeError(
                f"{module.__name__}.SERVICE_SPEC must be a {ServiceSpec.__name__} instance."
            )
        specs.append(service_spec)

    return tuple(specs)


@cache
def build_service_spec_catalog(
    extra_specs: tuple[ServiceSpec, ...] = (),
) -> tuple[ServiceSpec, ...]:
    """Build the full service catalog from discovered package service specs."""

    catalog = list(extra_specs)
    for package_name in _SERVICE_PACKAGE_ORDER:
        catalog.extend(discover_package_service_specs(package_name))
    return tuple(catalog)


def resolve_service_module(service_name: str) -> ModuleType:
    """Import and return the service module for one catalog tool name."""

    for package_name in _SERVICE_PACKAGE_ORDER:
        package = import_module(f"qspice_mcp.services.{package_name}")
        package_path = getattr(package, "__path__", None)
        if package_path is None:
            continue
        for module_info in iter_modules(package_path):
            if module_info.name.startswith("_"):
                continue
            if module_info.name != service_name:
                continue
            return import_module(f"{package.__name__}.{module_info.name}")
    raise KeyError(f"No service module registered for tool {service_name!r}.")


@cache
def build_service_callable_catalog() -> dict[str, object]:
    """Map implemented tool names to their primary service callables."""

    catalog: dict[str, object] = {}
    for package_name in _SERVICE_PACKAGE_ORDER:
        for spec in discover_package_service_specs(package_name):
            if spec.phase != "implemented":
                continue
            module = resolve_service_module(spec.name)
            service_fn = getattr(module, spec.name, None)
            if callable(service_fn):
                catalog[spec.name] = service_fn
    return catalog


__all__ = [
    "build_service_callable_catalog",
    "build_service_spec_catalog",
    "discover_package_service_specs",
    "resolve_service_module",
]
