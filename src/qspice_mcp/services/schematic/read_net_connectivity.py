"""Service for reporting net-level connectivity of a supported schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic._connectivity import build_connectivity
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class NetPin:
    """One component pin attached to a net."""

    reference: str
    pin: str


@dataclass(frozen=True, slots=True)
class NetConnectivity:
    """One electrical net with its attached pins."""

    net: str
    labeled: bool
    pin_count: int
    pins: tuple[NetPin, ...]


@dataclass(frozen=True, slots=True)
class NetConnectivityReport:
    """Connectivity summary for one schematic."""

    schematic_path: Path
    node_count: int
    component_count: int
    ground_present: bool
    nets: tuple[NetConnectivity, ...]


SERVICE_SPEC = ServiceSpec(
    name="read_net_connectivity",
    title="Read Net Connectivity",
    summary="Report electrical nets and the pins attached to each for a supported schematic.",
    phase="implemented",
    read_only=True,
)


def read_net_connectivity(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
) -> NetConnectivityReport:
    """Return the net-to-pin connectivity of one supported clean-room schematic."""

    resolved_path = validate_existing_file(
        schematic_path,
        workspace_root=workspace_root.resolve(strict=False),
        suffixes=(".qsch",),
    )
    model = build_connectivity(resolved_path)
    nets = tuple(
        NetConnectivity(
            net=group.name,
            labeled=group.labeled,
            pin_count=len(group.members),
            pins=tuple(
                NetPin(reference=member.reference, pin=member.pin) for member in group.members
            ),
        )
        for group in model.nets
    )
    return NetConnectivityReport(
        schematic_path=resolved_path,
        node_count=model.node_count,
        component_count=len(model.components),
        ground_present=model.ground_present,
        nets=nets,
    )


__all__ = [
    "SERVICE_SPEC",
    "NetConnectivity",
    "NetConnectivityReport",
    "NetPin",
    "read_net_connectivity",
]
