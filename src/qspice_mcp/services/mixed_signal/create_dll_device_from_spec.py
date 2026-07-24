"""Create one `.DLL` device (block + pins + optional source scaffold) from a pin spec.

Accepts a PinDef-style device specification — either inline (``device_name`` +
``pins``) or as a workspace JSON file (``spec_path``) — and performs the whole
device-authoring flow in one call: place the `.DLL` block with all pins, then
optionally generate the matching C++ source scaffold.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.mixed_signal.scaffold_dll_device_from_symbol import (
    scaffold_dll_device_from_symbol,
)
from qspice_mcp.services.schematic.add_dll_block import add_dll_block
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

DEVICE_SPEC_SCHEMA_VERSION = 1
_SUPPORTED_SPEC_SCHEMA_VERSION = DEVICE_SPEC_SCHEMA_VERSION
_PIN_DIRECTION_ALIASES = {
    "input": "input",
    "in": "input",
    "output": "output",
    "out": "output",
}


def device_spec_json_schema() -> dict[str, object]:
    """Return a JSON Schema fragment describing device spec v1."""

    return {
        "type": "object",
        "required": ["device_name", "pins"],
        "properties": {
            "schema_version": {"type": "integer", "const": DEVICE_SPEC_SCHEMA_VERSION},
            "device_name": {"type": "string", "minLength": 1},
            "description": {"type": "string"},
            "pins": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "direction"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "direction": {
                            "type": "string",
                            "enum": sorted(_PIN_DIRECTION_ALIASES),
                        },
                    },
                },
            },
        },
    }


def example_device_spec_document() -> dict[str, Any]:
    """Return the canonical v1 example document shipped with the server."""

    bundled = files("qspice_mcp.data.device_specs").joinpath("attiny85.v1.json")
    document: dict[str, Any] = json.loads(bundled.read_text(encoding="utf-8"))
    return document


@dataclass(frozen=True, slots=True)
class DevicePinSpec:
    """One normalized device pin from a PinDef-style specification."""

    name: str
    direction: str


@dataclass(frozen=True, slots=True)
class CreatedDllDeviceFromSpec:
    """Result of one spec-driven `.DLL` device creation."""

    schematic_path: Path
    output_path: Path
    reference: str
    device_name: str
    description: str | None
    pins: tuple[DevicePinSpec, ...]
    input_pin_names: tuple[str, ...]
    output_pin_names: tuple[str, ...]
    position_x: int
    position_y: int
    rotation_degrees: int
    spec_path: Path | None
    source_path: Path | None
    cmake_path: Path | None
    export_name: str | None
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="create_dll_device_from_spec",
    title="Create DLL Device From Spec",
    summary=(
        "Create one `.DLL` custom device from a PinDef-style pin specification "
        "(inline or workspace JSON): place the block with all pins in one call "
        "and optionally scaffold the matching C++ source."
    ),
    phase="implemented",
    read_only=False,
)


def _normalize_pin_entry(entry: object, *, index: int) -> DevicePinSpec:
    """Validate and normalize one raw pin entry from the spec."""

    if not isinstance(entry, dict):
        raise ValidationError(f"Device spec pins[{index}] must be an object with name/direction.")
    raw_name = entry.get("name")
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ValidationError(f"Device spec pins[{index}] requires a non-empty string name.")
    raw_direction = entry.get("direction")
    if not isinstance(raw_direction, str):
        raise ValidationError(
            f"Device spec pins[{index}] requires a direction of 'input' or 'output'."
        )
    direction = _PIN_DIRECTION_ALIASES.get(raw_direction.strip().lower())
    if direction is None:
        raise ValidationError(
            f"Device spec pins[{index}] has unsupported direction {raw_direction!r}; "
            "expected 'input' or 'output'."
        )
    return DevicePinSpec(name=raw_name.strip(), direction=direction)


def _normalize_pins(raw_pins: object) -> tuple[DevicePinSpec, ...]:
    """Validate the pins array and reject duplicates while preserving order."""

    if not isinstance(raw_pins, (list, tuple)) or not raw_pins:
        raise ValidationError("Device spec requires a non-empty pins array.")
    pins = tuple(_normalize_pin_entry(entry, index=index) for index, entry in enumerate(raw_pins))
    seen: set[str] = set()
    duplicates: list[str] = []
    for pin in pins:
        if pin.name in seen:
            duplicates.append(pin.name)
        seen.add(pin.name)
    if duplicates:
        raise ValidationError(
            "Device spec pin names must be unique. Duplicates: " + ", ".join(sorted(duplicates))
        )
    return pins


def _load_spec_file(
    spec_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[Path, dict[str, Any]]:
    """Read and validate one PinDef-style JSON spec file from the workspace."""

    resolved = validate_existing_file(spec_path, workspace_root=workspace_root, suffixes=(".json",))
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Device spec file {resolved.name} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"Device spec file {resolved.name} must contain a JSON object.")
    schema_version = payload.get("schema_version", _SUPPORTED_SPEC_SCHEMA_VERSION)
    if schema_version != _SUPPORTED_SPEC_SCHEMA_VERSION:
        raise ValidationError(
            f"Device spec schema_version {schema_version!r} is not supported; "
            f"expected {_SUPPORTED_SPEC_SCHEMA_VERSION}."
        )
    return resolved, payload


def create_dll_device_from_spec(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    settings: object,
    reference: str,
    device_name: str | None = None,
    pins: list[dict[str, object]] | tuple[dict[str, object], ...] | None = None,
    spec_path: str | Path | None = None,
    position_x: int = 0,
    position_y: int = 0,
    rotation_degrees: int = 0,
    scaffold_source: bool = True,
    output_dir: str | None = None,
    output_path: str | Path | None = None,
) -> CreatedDllDeviceFromSpec:
    """Create one `.DLL` device block (and optional source scaffold) from a pin spec."""

    resolved_workspace = workspace_root.resolve(strict=False)

    resolved_spec_path: Path | None = None
    description: str | None = None
    raw_pins: object = pins
    resolved_device_name = device_name

    if spec_path is not None:
        if pins is not None:
            raise ValidationError("Provide either spec_path or inline pins, not both.")
        resolved_spec_path, payload = _load_spec_file(spec_path, workspace_root=resolved_workspace)
        raw_pins = payload.get("pins")
        spec_device_name = payload.get("device_name")
        if resolved_device_name is None:
            if not isinstance(spec_device_name, str) or not spec_device_name.strip():
                raise ValidationError(
                    "Device spec file requires a non-empty device_name "
                    "(or pass device_name inline)."
                )
            resolved_device_name = spec_device_name
        raw_description = payload.get("description")
        if isinstance(raw_description, str) and raw_description.strip():
            description = raw_description.strip()
    elif pins is None:
        raise ValidationError("Provide a pins array inline or a spec_path JSON file.")

    if resolved_device_name is None or not resolved_device_name.strip():
        raise ValidationError("device_name is required when no spec_path is provided.")
    resolved_device_name = resolved_device_name.strip()

    normalized_pins = _normalize_pins(raw_pins)
    input_pin_names = tuple(pin.name for pin in normalized_pins if pin.direction == "input")
    output_pin_names = tuple(pin.name for pin in normalized_pins if pin.direction == "output")

    added = add_dll_block(
        schematic_path,
        workspace_root=workspace_root,
        reference=reference,
        device_name=resolved_device_name,
        input_pin_names=input_pin_names,
        output_pin_names=output_pin_names,
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=rotation_degrees,
        output_path=output_path,
    )

    source_path: Path | None = None
    cmake_path: Path | None = None
    export_name: str | None = None
    notes: list[str] = [
        f"Placed .DLL block {added.reference} ({resolved_device_name}) with "
        f"{len(input_pin_names)} input and {len(output_pin_names)} output pin(s)."
    ]
    if description is not None:
        notes.append(f"Spec description: {description}")

    if scaffold_source:
        scaffold = scaffold_dll_device_from_symbol(
            added.output_path,
            workspace_root=workspace_root,
            settings=settings,
            reference=added.reference,
            output_dir=output_dir,
        )
        source_path = scaffold.source_path
        cmake_path = scaffold.cmake_path
        export_name = scaffold.export_name
        notes.extend(scaffold.notes)
    else:
        notes.append("Source scaffold skipped (scaffold_source=false).")

    return CreatedDllDeviceFromSpec(
        schematic_path=added.schematic_path,
        output_path=added.output_path,
        reference=added.reference,
        device_name=resolved_device_name,
        description=description,
        pins=normalized_pins,
        input_pin_names=added.input_pin_names,
        output_pin_names=added.output_pin_names,
        position_x=position_x,
        position_y=position_y,
        rotation_degrees=rotation_degrees,
        spec_path=resolved_spec_path,
        source_path=source_path,
        cmake_path=cmake_path,
        export_name=export_name,
        notes=tuple(notes),
    )


__all__ = [
    "DEVICE_SPEC_SCHEMA_VERSION",
    "SERVICE_SPEC",
    "CreatedDllDeviceFromSpec",
    "DevicePinSpec",
    "create_dll_device_from_spec",
    "device_spec_json_schema",
    "example_device_spec_document",
]
