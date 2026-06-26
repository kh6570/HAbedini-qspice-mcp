"""Repo-owned schematic connectivity model built on the clean-room qsch parser.

This module reuses the clean-room schematic parser to derive a non-raising
net-connectivity view: every component pin is grouped into an electrical net,
conflicting net labels are reported instead of raising, and floating pins are
flagged. The model backs ``read_net_connectivity`` and the ERC lint tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from qspice_mcp.services.simulation._clean_room_netlist import (
    _normalize_net_name,
    _parse_qsch_schematic,
    _point_on_segment,
    _UnionFind,
)

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services.simulation._clean_room_netlist import Coordinate

_MIN_CONNECTED_POINTS = 2
_GROUND_NET = "0"


@dataclass(frozen=True, slots=True)
class PinConnection:
    """One component pin attached to an electrical net."""

    reference: str
    pin: str
    net: str
    point: Coordinate


@dataclass(frozen=True, slots=True)
class NetGroup:
    """One electrical net and the component pins attached to it."""

    name: str
    members: tuple[PinConnection, ...]
    labeled: bool


@dataclass(frozen=True, slots=True)
class ComponentConnection:
    """Connectivity-relevant metadata for one parsed component."""

    reference: str | None
    kind: str
    symbol: str
    value: str | None
    description: str | None
    pins: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NetLabelConflict:
    """A single electrical net carrying more than one explicit label."""

    labels: tuple[str, ...]
    references: tuple[str, ...]


@dataclass(slots=True)
class ConnectivityModel:
    """A non-raising connectivity view of one supported schematic."""

    node_count: int
    nets: tuple[NetGroup, ...]
    components: tuple[ComponentConnection, ...]
    conflicts: tuple[NetLabelConflict, ...]
    ground_present: bool
    pin_connections: tuple[PinConnection, ...] = field(default_factory=tuple)


def build_connectivity(schematic_path: Path) -> ConnectivityModel:  # noqa: PLR0912, PLR0915
    """Build a non-raising connectivity model for one supported clean-room schematic."""

    components, wires, nets, _ = _parse_qsch_schematic(schematic_path, allow_empty=True)

    union_find = _UnionFind()
    candidate_points: set[Coordinate] = set()
    for component in components:
        for pin in component.pins:
            candidate_points.add(pin.point)
    for wire in wires:
        candidate_points.add(wire.start)
        candidate_points.add(wire.end)
    for net in nets:
        candidate_points.add(net.point)
    for point in candidate_points:
        union_find.add(point)

    for wire in wires:
        on_segment = [
            point for point in candidate_points if _point_on_segment(point, wire.start, wire.end)
        ]
        if len(on_segment) < _MIN_CONNECTED_POINTS:
            continue
        root_point = on_segment[0]
        for point in on_segment[1:]:
            union_find.union(root_point, point)

    named_roots: dict[Coordinate, set[str]] = {}
    for wire in wires:
        if wire.name is None or not wire.name.strip():
            continue
        named_roots.setdefault(union_find.find(wire.start), set()).add(
            _normalize_net_name(wire.name)
        )
    for net in nets:
        if not net.name.strip():
            continue
        named_roots.setdefault(union_find.find(net.point), set()).add(_normalize_net_name(net.name))

    root_to_name: dict[Coordinate, str] = {}
    unnamed_index = 1
    for component in components:
        for pin in component.pins:
            root = union_find.find(pin.point)
            if root in root_to_name:
                continue
            labels = named_roots.get(root, set())
            if labels:
                root_to_name[root] = sorted(labels)[0]
            else:
                root_to_name[root] = f"N{unnamed_index:03d}"
                unnamed_index += 1

    # Group by final net name so same-named labels (for example two GND symbols)
    # collapse into one logical net, matching netlist node semantics.
    members_by_root: dict[Coordinate, list[PinConnection]] = {}
    members_by_name: dict[str, list[PinConnection]] = {}
    labeled_names: set[str] = set()
    pin_connections: list[PinConnection] = []
    for component in components:
        for pin in component.pins:
            root = union_find.find(pin.point)
            net_name = root_to_name[root]
            connection = PinConnection(
                reference=component.reference or "?",
                pin=pin.name,
                net=net_name,
                point=pin.point,
            )
            pin_connections.append(connection)
            members_by_root.setdefault(root, []).append(connection)
            members_by_name.setdefault(net_name, []).append(connection)
            if named_roots.get(root):
                labeled_names.add(net_name)

    net_groups = [
        NetGroup(
            name=name,
            members=tuple(members),
            labeled=name in labeled_names,
        )
        for name, members in members_by_name.items()
    ]
    net_groups.sort(key=lambda group: group.name)

    conflicts: list[NetLabelConflict] = []
    for root, labels in named_roots.items():
        if len(labels) <= 1:
            continue
        references = tuple(
            sorted(
                {member.reference for member in members_by_root.get(root, []) if member.reference}
            )
        )
        conflicts.append(NetLabelConflict(labels=tuple(sorted(labels)), references=references))

    component_views = tuple(
        ComponentConnection(
            reference=component.reference,
            kind=component.kind,
            symbol=component.symbol,
            value=component.value,
            description=component.description,
            pins=tuple(pin.name for pin in sorted(component.pins, key=lambda item: item.order)),
        )
        for component in components
    )

    ground_present = any(group.name == _GROUND_NET for group in net_groups)

    return ConnectivityModel(
        node_count=len(net_groups),
        nets=tuple(net_groups),
        components=component_views,
        conflicts=tuple(conflicts),
        ground_present=ground_present,
        pin_connections=tuple(pin_connections),
    )


__all__ = [
    "ComponentConnection",
    "ConnectivityModel",
    "NetGroup",
    "NetLabelConflict",
    "PinConnection",
    "build_connectivity",
]
