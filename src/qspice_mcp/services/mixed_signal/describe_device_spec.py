"""Describe the PinDef-style device specification JSON format (v1)."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.services.mixed_signal.create_dll_device_from_spec import (
    DEVICE_SPEC_SCHEMA_VERSION,
    device_spec_json_schema,
    example_device_spec_document,
)
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="describe_device_spec",
    title="Describe Device Spec",
    summary=(
        "Return the v1 PinDef-style device-spec JSON schema and a bundled "
        "example for one-call `.DLL` device creation from a datasheet pin map."
    ),
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class DeviceSpecDescription:
    """Machine-readable description of device spec v1."""

    schema_version: int
    pin_directions: tuple[str, ...]
    json_schema: dict[str, object]
    example_document: dict[str, object]
    bundled_example_path: str
    notes: tuple[str, ...]


def describe_device_spec() -> DeviceSpecDescription:
    """Return schema and example content for device spec v1."""

    return DeviceSpecDescription(
        schema_version=DEVICE_SPEC_SCHEMA_VERSION,
        pin_directions=("input", "output"),
        json_schema=device_spec_json_schema(),
        example_document=example_device_spec_document(),
        bundled_example_path="attiny85.v1.json",
        notes=(
            "Write the JSON file under the workspace and pass its path to "
            "create_dll_device_from_spec as spec_path (or pass device_name + "
            "pins inline and skip the file).",
            "Pin order in the spec becomes the pin order on the `.DLL` block "
            "and in the generated C++ uData bindings.",
            "Direction accepts input/in and output/out; bidirectional pins are "
            "not supported — model them as an input/output pair.",
            "create_dll_device_from_spec scaffolds per-instance C++ source by "
            "default; pass scaffold_source=false to place the block only.",
        ),
    )


__all__ = [
    "SERVICE_SPEC",
    "DeviceSpecDescription",
    "describe_device_spec",
]
