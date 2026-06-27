"""Deprecated alias for rotating one placed schematic component.

Prefer ``set_component_position`` (the unified placement tool), which rotates,
moves, preserves attached connections, and normalizes refdes/value text in one
call. This tool now delegates to that path with rotation only; it is retained
as a backward-compatible alias and will be removed in a future breaking release.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.set_component_position import set_component_position
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class ComponentRotationUpdate:
    """Metadata for one component rotation edit."""

    schematic_path: Path
    output_path: Path
    reference: str
    rotation_degrees: int
    preserve_connections: bool = True
    rewired_endpoints: int = 0
    normalize_text: bool = True
    normalized_text_count: int = 0


SERVICE_SPEC = ServiceSpec(
    name="set_component_rotation",
    title="Set Component Rotation",
    summary=(
        "Deprecated alias for set_component_position (rotation only). Rotates one placed "
        "component in 45-degree steps; preserves attached connections and normalizes "
        "refdes/value text by default. Prefer set_component_position."
    ),
    phase="implemented",
    read_only=False,
)


def set_component_rotation(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    reference: str,
    rotation_degrees: int,
    preserve_connections: bool = True,
    normalize_text: bool = True,
    output_path: str | Path | None = None,
) -> ComponentRotationUpdate:
    """Rotate one component (delegates to the unified set_component_position path)."""

    placement = set_component_position(
        schematic_path,
        workspace_root=workspace_root,
        reference=reference,
        rotation_degrees=rotation_degrees,
        preserve_connections=preserve_connections,
        normalize_text=normalize_text,
        output_path=output_path,
    )
    return ComponentRotationUpdate(
        schematic_path=placement.schematic_path,
        output_path=placement.output_path,
        reference=placement.reference,
        rotation_degrees=placement.rotation_degrees,
        preserve_connections=placement.preserve_connections,
        rewired_endpoints=placement.rewired_endpoints,
        normalize_text=placement.normalize_text,
        normalized_text_count=placement.normalized_text_count,
    )


__all__ = ["SERVICE_SPEC", "ComponentRotationUpdate", "set_component_rotation"]
