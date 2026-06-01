"""Service for summarizing Operating Point device data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform.read_device_operating_points import (
    DeviceOperatingPoint,
    NodeVoltage,
    OperatingPointMetric,
    read_device_operating_points,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceOperatingPointExtremum:
    """One notable device metric selected from an operating-point catalog."""

    reference: str
    family: str
    model: str | None
    metric_name: str
    trace_name: str
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class OperatingPointFamilySummary:
    """Compact summary for one device family."""

    family: str
    device_count: int
    models: tuple[str, ...]
    total_power_w: float | None


@dataclass(frozen=True, slots=True)
class DeviceOperatingPointSummary:
    """Compact summary of device operating-point data."""

    raw_path: Path
    netlist_path: Path | None
    plot_name: str | None
    device_count: int
    node_count: int
    family_summaries: tuple[OperatingPointFamilySummary, ...]
    highest_dissipation: DeviceOperatingPointExtremum | None
    lowest_dissipation: DeviceOperatingPointExtremum | None
    largest_abs_current: DeviceOperatingPointExtremum | None
    highest_node_voltage: NodeVoltage | None
    lowest_node_voltage: NodeVoltage | None
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="summarize_device_operating_points",
    title="Summarize Device Operating Points",
    summary="Return compact family-level and extremum summaries for one Operating Point raw file.",
    phase="implemented",
)


def _render_extremum(
    device: DeviceOperatingPoint,
    metric: OperatingPointMetric,
) -> DeviceOperatingPointExtremum:
    return DeviceOperatingPointExtremum(
        reference=device.reference,
        family=device.family,
        model=device.model,
        metric_name=metric.name,
        trace_name=metric.trace_name,
        value=metric.value,
        unit=metric.unit,
    )


def summarize_device_operating_points(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    netlist_path: str | Path | None = None,
) -> DeviceOperatingPointSummary:
    """Summarize operating-point data by family and notable extrema."""

    catalog = read_device_operating_points(
        raw_path,
        workspace_root=workspace_root.resolve(strict=False),
        netlist_path=netlist_path,
    )

    family_summaries: list[OperatingPointFamilySummary] = []
    for group in catalog.groups:
        group_devices = tuple(
            device
            for device in catalog.devices
            if device.family == group.family and device.model == group.model
        )
        power_values = tuple(
            metric.value
            for device in group_devices
            for metric in device.metrics
            if metric.name == "power"
        )
        models = tuple(
            sorted(
                {device.model for device in group_devices if device.model is not None},
                key=str.lower,
            )
        )
        family_summaries.append(
            OperatingPointFamilySummary(
                family=group.family,
                device_count=group.device_count,
                models=models,
                total_power_w=sum(power_values) if power_values else None,
            )
        )

    power_candidates = tuple(
        (device, metric)
        for device in catalog.devices
        for metric in device.metrics
        if metric.name == "power"
    )
    current_candidates = tuple(
        (device, metric)
        for device in catalog.devices
        for metric in device.metrics
        if metric.unit == "A"
    )

    highest_dissipation = (
        _render_extremum(*max(power_candidates, key=lambda item: item[1].value))
        if power_candidates
        else None
    )
    lowest_dissipation = (
        _render_extremum(*min(power_candidates, key=lambda item: item[1].value))
        if power_candidates
        else None
    )
    largest_abs_current = (
        _render_extremum(*max(current_candidates, key=lambda item: abs(item[1].value)))
        if current_candidates
        else None
    )
    highest_node_voltage = max(
        catalog.node_voltages,
        key=lambda item: item.voltage_v,
        default=None,
    )
    lowest_node_voltage = min(
        catalog.node_voltages,
        key=lambda item: item.voltage_v,
        default=None,
    )

    return DeviceOperatingPointSummary(
        raw_path=catalog.raw_path,
        netlist_path=catalog.netlist_path,
        plot_name=catalog.plot_name,
        device_count=catalog.device_count,
        node_count=catalog.node_count,
        family_summaries=tuple(family_summaries),
        highest_dissipation=highest_dissipation,
        lowest_dissipation=lowest_dissipation,
        largest_abs_current=largest_abs_current,
        highest_node_voltage=highest_node_voltage,
        lowest_node_voltage=lowest_node_voltage,
        warnings=catalog.warnings,
    )


__all__ = [
    "SERVICE_SPEC",
    "DeviceOperatingPointExtremum",
    "DeviceOperatingPointSummary",
    "OperatingPointFamilySummary",
    "summarize_device_operating_points",
]
