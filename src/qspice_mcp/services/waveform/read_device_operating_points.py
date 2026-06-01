"""Service for reading device operating-point data from an Operating Point raw file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.waveform import (
    get_plot_name,
    get_signal_names,
    open_raw_reader,
    to_wave_array,
)
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


_TRACE_PATTERN = re.compile(r"^(?P<metric>[A-Za-z]+)\((?P<target>[^)]+)\)$")
_MODEL_PATTERN = re.compile(r"^\.model\s+(?P<name>\S+)\s+(?P<kind>\S+)", re.IGNORECASE)
_COMMENT_PREFIXES = ("*", ";")
_NETLIST_SUFFIXES = (".net", ".cir")
_MIN_SUBCKT_TOKENS = 3
_MIN_TWO_NODE_DEVICE_TOKENS = 4
_MIN_THREE_NODE_MODEL_TOKENS = 5
_MIN_FOUR_NODE_MODEL_TOKENS = 6
_FAMILY_BY_PREFIX = {
    "R": "resistor",
    "C": "capacitor",
    "L": "inductor",
    "V": "voltage_source",
    "I": "current_source",
    "D": "diode",
    "Q": "bjt",
    "M": "mosfet",
    "J": "jfet",
    "X": "subcircuit",
    "B": "behavioral_source",
    "E": "voltage_controlled_source",
    "F": "current_controlled_source",
    "G": "voltage_controlled_source",
    "H": "current_controlled_source",
}
_METRIC_NAMES = {
    "i": "current",
    "p": "power",
    "id": "drain_current",
    "is": "source_current",
    "ig": "gate_current",
    "ic": "collector_current",
    "ie": "emitter_current",
}


@dataclass(frozen=True, slots=True)
class OperatingPointMetric:
    """One scalar operating-point metric reported for a device."""

    name: str
    trace_name: str
    value: float
    unit: str


@dataclass(frozen=True, slots=True)
class NodeVoltage:
    """One node voltage sampled from an Operating Point plot."""

    node: str
    voltage_v: float
    trace_name: str


@dataclass(frozen=True, slots=True)
class DeviceOperatingPoint:
    """Operating-point metrics for one device reference."""

    reference: str
    family: str
    model: str | None
    model_type: str | None
    nodes: tuple[str, ...]
    metrics: tuple[OperatingPointMetric, ...]


@dataclass(frozen=True, slots=True)
class OperatingPointGroup:
    """Grouping of devices by inferred family and model."""

    family: str
    model: str | None
    device_count: int
    references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeviceOperatingPointCatalog:
    """Device and node operating-point data resolved from one raw artifact."""

    raw_path: Path
    netlist_path: Path | None
    plot_name: str | None
    device_count: int
    node_count: int
    groups: tuple[OperatingPointGroup, ...]
    devices: tuple[DeviceOperatingPoint, ...]
    node_voltages: tuple[NodeVoltage, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _DeviceMetadata:
    reference: str
    family: str
    model: str | None
    model_type: str | None
    nodes: tuple[str, ...]


SERVICE_SPEC = ServiceSpec(
    name="read_device_operating_points",
    title="Read Device Operating Points",
    summary=(
        "Read device operating-point currents, powers, and node voltages from one "
        "Operating Point raw artifact."
    ),
    phase="implemented",
)


def _reference_key(value: str) -> str:
    return value.strip().lower()


def _infer_family(reference: str) -> str:
    prefix = reference.strip()[:1].upper()
    return _FAMILY_BY_PREFIX.get(prefix, "device")


def _metric_unit(raw_metric: str) -> str:
    if raw_metric.upper().startswith("P"):
        return "W"
    if raw_metric.upper().startswith("I"):
        return "A"
    return "arb"


def _metric_name(raw_metric: str, *, family: str) -> str:
    normalized = raw_metric.lower()
    if normalized == "ib":
        return "base_current" if family == "bjt" else "bulk_current"
    return _METRIC_NAMES.get(normalized, normalized)


def _resolve_associated_netlist(
    netlist_path: str | Path | None,
    *,
    raw_path: Path,
    workspace_root: Path,
) -> Path | None:
    if netlist_path is not None:
        return validate_existing_file(
            netlist_path,
            workspace_root=workspace_root,
            suffixes=_NETLIST_SUFFIXES,
        )
    for suffix in _NETLIST_SUFFIXES:
        candidate = raw_path.with_suffix(suffix)
        if candidate.is_file():
            return candidate.resolve(strict=False)
    return None


def _normalized_netlist_lines(text: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("+") and lines:
            lines[-1] = f"{lines[-1]} {stripped[1:].strip()}"
            continue
        lines.append(stripped)
    return tuple(lines)


def _parse_model_kinds(lines: tuple[str, ...]) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for line in lines:
        match = _MODEL_PATTERN.match(line)
        if match is None:
            continue
        kinds[match.group("name").upper()] = match.group("kind").lower()
    return kinds


def _parse_device_line(
    line: str,
    *,
    model_kinds: dict[str, str],
) -> _DeviceMetadata | None:
    if not line or line.startswith(_COMMENT_PREFIXES) or line.startswith("."):
        return None
    tokens = line.split()
    if not tokens:
        return None
    reference = tokens[0]
    family = _infer_family(reference)
    prefix = reference[:1].upper()
    model: str | None = None
    nodes: tuple[str, ...] = ()

    if prefix in {"R", "C", "L", "V", "I"} and len(tokens) >= _MIN_TWO_NODE_DEVICE_TOKENS:
        nodes = tuple(tokens[1:3])
    elif prefix == "D" and len(tokens) >= _MIN_TWO_NODE_DEVICE_TOKENS:
        nodes = tuple(tokens[1:3])
        model = tokens[3]
    elif prefix == "M" and len(tokens) >= _MIN_FOUR_NODE_MODEL_TOKENS:
        nodes = tuple(tokens[1:5])
        model = tokens[5]
    elif prefix == "J" and len(tokens) >= _MIN_THREE_NODE_MODEL_TOKENS:
        nodes = tuple(tokens[1:4])
        model = tokens[4]
    elif prefix == "Q":
        if len(tokens) >= _MIN_FOUR_NODE_MODEL_TOKENS and tokens[5].upper() in model_kinds:
            nodes = tuple(tokens[1:5])
            model = tokens[5]
        elif len(tokens) >= _MIN_THREE_NODE_MODEL_TOKENS:
            nodes = tuple(tokens[1:4])
            model = tokens[4]
    elif prefix == "X" and len(tokens) >= _MIN_SUBCKT_TOKENS:
        nodes = tuple(tokens[1:-1])
        model = tokens[-1]
    elif prefix in {"B", "E", "F", "G", "H"} and len(tokens) >= _MIN_SUBCKT_TOKENS:
        nodes = tuple(tokens[1:3])

    model_type = model_kinds.get(model.upper()) if model is not None else None
    return _DeviceMetadata(
        reference=reference,
        family=family,
        model=model,
        model_type=model_type,
        nodes=nodes,
    )


def _read_netlist_metadata(netlist_path: Path) -> dict[str, _DeviceMetadata]:
    lines = _normalized_netlist_lines(netlist_path.read_text(encoding="utf-8", errors="replace"))
    model_kinds = _parse_model_kinds(lines)
    metadata: dict[str, _DeviceMetadata] = {}
    for line in lines:
        parsed = _parse_device_line(line, model_kinds=model_kinds)
        if parsed is None:
            continue
        metadata[_reference_key(parsed.reference)] = parsed
    return metadata


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


def read_device_operating_points(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    netlist_path: str | Path | None = None,
) -> DeviceOperatingPointCatalog:
    """Read device operating-point metrics from one `.qraw` Operating Point artifact."""

    normalized_workspace = workspace_root.resolve(strict=False)
    reader, resolved_raw_path = open_raw_reader(raw_path, workspace_root=normalized_workspace)
    plot_name = get_plot_name(reader)
    if (plot_name or "").strip().lower() != "operating point":
        raise ValueError(
            "Device operating-point inspection requires a `.qraw` artifact with plot name "
            "`Operating Point`."
        )

    resolved_netlist_path = _resolve_associated_netlist(
        netlist_path,
        raw_path=resolved_raw_path,
        workspace_root=normalized_workspace,
    )
    warnings: list[str] = []
    metadata_by_reference = (
        _read_netlist_metadata(resolved_netlist_path) if resolved_netlist_path is not None else {}
    )
    if resolved_netlist_path is None:
        warnings.append(
            "No sibling .net or .cir file was found, so device node and "
            "model metadata may be incomplete."
        )

    node_voltages: list[NodeVoltage] = []
    metrics_by_reference: dict[str, list[tuple[str, str, float, str]]] = {}
    reference_names: dict[str, str] = {}

    for signal_name in get_signal_names(reader):
        match = _TRACE_PATTERN.match(signal_name)
        if match is None:
            warnings.append(
                f"Signal '{signal_name}' does not match an operating-point trace pattern."
            )
            continue
        wave = to_wave_array(reader.get_wave(signal_name, step=0))
        if wave.size == 0:
            warnings.append(f"Signal '{signal_name}' did not contain any operating-point sample.")
            continue
        value = float(wave[0])
        raw_metric = match.group("metric")
        target = match.group("target")
        if raw_metric.upper() == "V":
            node_voltages.append(NodeVoltage(node=target, voltage_v=value, trace_name=signal_name))
            continue

        key = _reference_key(target)
        reference_names.setdefault(key, target)
        metrics_by_reference.setdefault(key, []).append(
            (raw_metric, signal_name, value, _metric_unit(raw_metric))
        )

    devices: list[DeviceOperatingPoint] = []
    for reference_key, entries in sorted(metrics_by_reference.items()):
        metadata = metadata_by_reference.get(reference_key)
        reference = metadata.reference if metadata is not None else reference_names[reference_key]
        family = metadata.family if metadata is not None else _infer_family(reference)
        model = metadata.model if metadata is not None else None
        model_type = metadata.model_type if metadata is not None else None
        metrics = tuple(
            OperatingPointMetric(
                name=_metric_name(raw_metric, family=family),
                trace_name=trace_name,
                value=value,
                unit=unit,
            )
            for raw_metric, trace_name, value, unit in sorted(
                entries, key=lambda item: item[1].lower()
            )
        )
        devices.append(
            DeviceOperatingPoint(
                reference=reference,
                family=family,
                model=model,
                model_type=model_type,
                nodes=metadata.nodes if metadata is not None else (),
                metrics=metrics,
            )
        )

    rendered_nodes = tuple(sorted(node_voltages, key=lambda node: node.node.lower()))
    rendered_devices = tuple(sorted(devices, key=lambda device: device.reference.lower()))
    return DeviceOperatingPointCatalog(
        raw_path=resolved_raw_path,
        netlist_path=resolved_netlist_path,
        plot_name=plot_name,
        device_count=len(rendered_devices),
        node_count=len(rendered_nodes),
        groups=_group_devices(rendered_devices),
        devices=rendered_devices,
        node_voltages=rendered_nodes,
        warnings=tuple(warnings),
    )


__all__ = [
    "SERVICE_SPEC",
    "DeviceOperatingPoint",
    "DeviceOperatingPointCatalog",
    "NodeVoltage",
    "OperatingPointGroup",
    "OperatingPointMetric",
    "read_device_operating_points",
]
