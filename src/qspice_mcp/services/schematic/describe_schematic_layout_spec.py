"""Describe the schematic layout specification JSON format (v1)."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.services.schematic._layout_spec import (
    LAYOUT_SPEC_SCHEMA_VERSION,
    example_layout_spec_document,
    layout_spec_json_schema,
)
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="describe_schematic_layout_spec",
    title="Describe Schematic Layout Spec",
    summary=(
        "Return the v1 JSON layout-spec schema, placement modes, and a bundled "
        "example for batch component placement without large coordinate tables."
    ),
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class SchematicLayoutSpecDescription:
    """Machine-readable description of layout spec v1."""

    schema_version: int
    placement_modes: tuple[str, ...]
    json_schema: dict[str, object]
    example_document: dict[str, object]
    bundled_example_path: str
    notes: tuple[str, ...]


def describe_schematic_layout_spec() -> SchematicLayoutSpecDescription:
    """Return schema and example content for layout spec v1."""

    return SchematicLayoutSpecDescription(
        schema_version=LAYOUT_SPEC_SCHEMA_VERSION,
        placement_modes=("auto", "grid", "absolute"),
        json_schema=layout_spec_json_schema(),
        example_document=example_layout_spec_document(),
        bundled_example_path="scratch_power_stage.v1.json",
        notes=(
            "Write the JSON file under the workspace and pass its path "
            "to apply_schematic_layout_spec.",
            "placement=auto uses collision-aware grid scanning "
            "(same engine as suggest_component_placement).",
            "placement=grid uses grid.origin + column/row * step without overlap checks.",
            "placement=absolute uses explicit position_x/position_y "
            "(for human-tuned rows like scratch.md).",
            "Wires, junctions, and labels are not part of layout spec v1; "
            "add them with dedicated tools.",
        ),
    )


__all__ = [
    "SERVICE_SPEC",
    "SchematicLayoutSpecDescription",
    "describe_schematic_layout_spec",
]
