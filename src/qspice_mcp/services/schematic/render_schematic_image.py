"""Service for rendering a supported schematic to a PNG preview image."""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")

from typing import TYPE_CHECKING

from matplotlib import pyplot as plt

from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
    validate_existing_file,
)
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._clean_room_netlist import _parse_qsch_schematic

if TYPE_CHECKING:
    from pathlib import Path

_WIRE_COLOR = "#1f77b4"
_PIN_COLOR = "#2ca02c"
_NET_COLOR = "#d62728"
_JUNCTION_COLOR = "#000000"


@dataclass(frozen=True, slots=True)
class RenderedSchematicImage:
    """One rendered schematic preview artifact."""

    schematic_path: Path
    image_path: Path
    format: str
    component_count: int
    wire_count: int
    net_label_count: int


SERVICE_SPEC = ServiceSpec(
    name="render_schematic_image",
    title="Render Schematic Image",
    summary="Render a supported schematic (wires, junctions, components, labels) to a PNG image.",
    phase="implemented",
    read_only=False,
    idempotent=True,
)


def render_schematic_image(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    overwrite: bool = False,
) -> RenderedSchematicImage:
    """Render one supported clean-room schematic to a PNG image inside the workspace."""

    resolved_workspace = workspace_root.resolve(strict=False)
    resolved_path = validate_existing_file(
        schematic_path,
        workspace_root=resolved_workspace,
        suffixes=(".qsch",),
    )
    image_path = resolve_workspace_output_path(
        output_path,
        workspace_root=resolved_workspace,
        default=resolved_path.with_name(f"{resolved_path.stem}-schematic.png"),
        suffixes=(".png",),
    )
    if image_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing image: {image_path}")

    components, wires, nets, _ = _parse_qsch_schematic(resolved_path, allow_empty=True)

    figure, axes = plt.subplots(figsize=(11.0, 8.5), constrained_layout=True)

    for wire in wires:
        axes.plot(
            [wire.start[0], wire.end[0]],
            [wire.start[1], wire.end[1]],
            color=_WIRE_COLOR,
            linewidth=1.2,
            zorder=1,
        )

    net_label_count = 0
    for net in nets:
        if net.name.strip():
            net_label_count += 1
            axes.plot(
                net.point[0], net.point[1], marker="o", markersize=4, color=_NET_COLOR, zorder=3
            )
            axes.text(
                net.point[0],
                net.point[1],
                f" {net.name}",
                fontsize=7,
                color=_NET_COLOR,
                va="center",
                zorder=4,
            )
        else:
            axes.plot(
                net.point[0],
                net.point[1],
                marker="o",
                markersize=4,
                color=_JUNCTION_COLOR,
                zorder=3,
            )

    for component in components:
        for pin in component.pins:
            axes.plot(
                pin.point[0],
                pin.point[1],
                marker="s",
                markersize=3,
                color=_PIN_COLOR,
                zorder=2,
            )
        label = component.reference or "?"
        if component.value:
            label = f"{label}\n{component.value}"
        axes.text(
            component.anchor[0],
            component.anchor[1],
            label,
            fontsize=7,
            ha="center",
            va="center",
            zorder=5,
        )

    axes.set_title(resolved_path.name)
    axes.set_aspect("equal", adjustable="datalim")
    axes.invert_yaxis()
    axes.grid(True, alpha=0.2)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(image_path, format="png", dpi=160)
    plt.close(figure)

    return RenderedSchematicImage(
        schematic_path=resolved_path,
        image_path=image_path,
        format="png",
        component_count=len(components),
        wire_count=len(wires),
        net_label_count=net_label_count,
    )


__all__ = ["SERVICE_SPEC", "RenderedSchematicImage", "render_schematic_image"]
