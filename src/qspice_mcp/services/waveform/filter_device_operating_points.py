"""Service for filtering Operating Point device data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_device_operating_points import (
    DeviceOperatingPoint,
    NodeVoltage,
    OperatingPointGroup,
    read_device_operating_points,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceOperatingPointFilters:
    """Resolved filters applied to a device operating-point query."""

    families: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    reference_pattern: str | None = None
    metric_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FilteredDeviceOperatingPointCatalog:
    """Filtered view over one device operating-point catalog."""

    raw_path: Path
    netlist_path: Path | None
    plot_name: str | None
    original_device_count: int
    device_count: int
    node_count: int
    groups: tuple[OperatingPointGroup, ...]
    devices: tuple[DeviceOperatingPoint, ...]
    node_voltages: tuple[NodeVoltage, ...]
    applied_filters: DeviceOperatingPointFilters
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="filter_device_operating_points",
    title="Filter Device Operating Points",
    summary="Filter device operating-point data by family, model, reference, and metric presence.",
    phase="implemented",
)


def _group_devices(devices: tuple[DeviceOperatingPoint, ...]) -> tuple[OperatingPointGroup, ...]:
    grouped: dict[tuple[str, str | None], list[str]] = {}
    for device in devices:
        grouped.setdefault((device.family, device.model), []).append(device.reference)
    return tuple(
        OperatingPointGroup(
            family=family,
            model=model,
            device_count=len(references),
            references=tuple(sorted(references, key=str.lower)),
        )
        for (family, model), references in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1] or "")
        )
    )


def filter_device_operating_points(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    netlist_path: str | Path | None = None,
    families: tuple[str, ...] | list[str] | None = None,
    models: tuple[str, ...] | list[str] | None = None,
    references: tuple[str, ...] | list[str] | None = None,
    reference_pattern: str | None = None,
    metric_names: tuple[str, ...] | list[str] | None = None,
) -> FilteredDeviceOperatingPointCatalog:
    """Filter one operating-point catalog by device metadata and metric presence."""

    catalog = read_device_operating_points(
        raw_path,
        workspace_root=workspace_root.resolve(strict=False),
        netlist_path=netlist_path,
    )
    normalized_families = tuple(
        sorted({value.strip().lower() for value in families or () if value.strip()})
    )
    normalized_models = tuple(
        sorted({value.strip().lower() for value in models or () if value.strip()})
    )
    normalized_references = tuple(
        sorted({value.strip().lower() for value in references or () if value.strip()})
    )
    normalized_metrics = tuple(
        sorted({value.strip().lower() for value in metric_names or () if value.strip()})
    )
    normalized_metric_set = set(normalized_metrics)
    compiled_pattern = re.compile(reference_pattern, re.IGNORECASE) if reference_pattern else None

    filtered_devices = tuple(
        device
        for device in catalog.devices
        if (not normalized_families or device.family.lower() in normalized_families)
        and (not normalized_models or (device.model or "").lower() in normalized_models)
        and (not normalized_references or device.reference.lower() in normalized_references)
        and (compiled_pattern is None or compiled_pattern.search(device.reference) is not None)
        and (
            not normalized_metric_set
            or normalized_metric_set.issubset({metric.name.lower() for metric in device.metrics})
        )
    )

    return FilteredDeviceOperatingPointCatalog(
        raw_path=catalog.raw_path,
        netlist_path=catalog.netlist_path,
        plot_name=catalog.plot_name,
        original_device_count=catalog.device_count,
        device_count=len(filtered_devices),
        node_count=catalog.node_count,
        groups=_group_devices(filtered_devices),
        devices=filtered_devices,
        node_voltages=catalog.node_voltages,
        applied_filters=DeviceOperatingPointFilters(
            families=normalized_families,
            models=normalized_models,
            references=normalized_references,
            reference_pattern=reference_pattern,
            metric_names=normalized_metrics,
        ),
        warnings=catalog.warnings,
    )


__all__ = [
    "SERVICE_SPEC",
    "DeviceOperatingPointFilters",
    "FilteredDeviceOperatingPointCatalog",
    "filter_device_operating_points",
]
