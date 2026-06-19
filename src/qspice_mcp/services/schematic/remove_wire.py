"""Service for removing one wire segment from a schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from qspice_mcp.services._backends.schematic_editor import remove_wire as remove_wire_segment
from qspice_mcp.services._backends.schematic_editor import resolve_wire_points
from qspice_mcp.services._internals.schematic_edits import edit_schematic
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class RemovedWire:
    """Metadata for one removed wire segment."""

    schematic_path: Path
    output_path: Path
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    net_name: str


SERVICE_SPEC = ServiceSpec(
    name="remove_wire",
    title="Remove Wire",
    summary="Remove one wire segment from a schematic by endpoints or pin selectors.",
    phase="implemented",
    read_only=False,
)


def remove_wire(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    start_x: int | None = None,
    start_y: int | None = None,
    end_x: int | None = None,
    end_y: int | None = None,
    start_reference: str | None = None,
    start_pin: str | None = None,
    end_reference: str | None = None,
    end_pin: str | None = None,
    net_name: str | None = None,
    output_path: str | Path | None = None,
) -> RemovedWire:
    """Remove one wire segment and persist the edited schematic."""

    normalized_net_name: str | None = None
    resolved_start: tuple[int, int] | None = None
    resolved_end: tuple[int, int] | None = None

    def build_point(x: int | None, y: int | None, *, endpoint_name: str) -> tuple[int, int] | None:
        if x is None and y is None:
            return None
        if x is None or y is None:
            raise ValueError(
                f"Wire {endpoint_name} coordinates require both "
                f"{endpoint_name}_x and {endpoint_name}_y."
            )
        return x, y

    def apply_wire_edit(editor: object) -> None:
        nonlocal normalized_net_name, resolved_end, resolved_start
        resolved_start, resolved_end = resolve_wire_points(
            cast("Any", editor),
            start=build_point(start_x, start_y, endpoint_name="start"),
            end=build_point(end_x, end_y, endpoint_name="end"),
            start_reference=start_reference,
            start_pin=start_pin,
            end_reference=end_reference,
            end_pin=end_pin,
        )
        normalized_net_name = remove_wire_segment(
            cast("Any", editor),
            start=resolved_start,
            end=resolved_end,
            net_name=net_name,
        )

    resolved_path, saved_path = edit_schematic(
        schematic_path,
        workspace_root=workspace_root,
        output_path=output_path,
        apply_edit=apply_wire_edit,
    )
    if normalized_net_name is None or resolved_start is None or resolved_end is None:
        raise RuntimeError("Wire removal did not report resolved endpoints.")
    return RemovedWire(
        schematic_path=resolved_path,
        output_path=saved_path,
        start_x=resolved_start[0],
        start_y=resolved_start[1],
        end_x=resolved_end[0],
        end_y=resolved_end[1],
        net_name=normalized_net_name,
    )


__all__ = ["SERVICE_SPEC", "RemovedWire", "remove_wire"]
