"""Service for creating a runnable starter schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services._backends.clean_room_schematic import write_starter_schematic
from qspice_mcp.services._backends.schematic_editor import (
    add_net_label,
    add_simple_component,
    add_wire,
    bootstrap_blank_schematic,
    load_qsch_editor_factory,
    resolve_component_pin_position,
    resolve_schematic_output_path,
)
from qspice_mcp.services._internals.schematic_edits import save_editor_as
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_STARTER_SOURCE_POSITION = (400, 400)
_STARTER_LOAD_POSITION = (800, 400)


@dataclass(frozen=True, slots=True)
class CreatedStarterSchematic:
    """Metadata for one generated starter schematic."""

    output_path: Path
    overwritten: bool
    source_reference: str
    source_value: str
    load_reference: str
    load_value: str
    input_net_name: str
    analysis_instruction: str


SERVICE_SPEC = ServiceSpec(
    name="create_starter_schematic",
    title="Create Starter Schematic",
    summary="Create a runnable source-load starter schematic in one call.",
    phase="implemented",
    read_only=False,
)


def create_starter_schematic(
    output_path: str | Path,
    *,
    workspace_root: Path,
    overwrite: bool = False,
    source_reference: str = "V1",
    source_value: str | int | float = "10",
    load_reference: str = "R1",
    load_value: str | int | float = "1k",
    input_net_name: str = "VIN",
    analysis_instruction: str = ".op",
) -> CreatedStarterSchematic:
    """Create a saved starter schematic with a source, load, labels, and analysis."""

    destination = resolve_schematic_output_path(
        output_path,
        workspace_root=workspace_root.resolve(strict=False),
        default=workspace_root / "starter.qsch",
    )
    existed = destination.exists()
    if existed and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing schematic: {destination}")

    editor_factory, backend_name = load_qsch_editor_factory()
    if editor_factory is None or backend_name is None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_starter_schematic(
            destination,
            source_reference=source_reference,
            source_value=source_value,
            load_reference=load_reference,
            load_value=load_value,
            input_net_name=input_net_name,
            analysis_instruction=analysis_instruction,
        )
        return CreatedStarterSchematic(
            output_path=destination.resolve(strict=False),
            overwritten=existed,
            source_reference=source_reference,
            source_value=str(source_value),
            load_reference=load_reference,
            load_value=str(load_value),
            input_net_name=input_net_name,
            analysis_instruction=analysis_instruction,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        editor = editor_factory(str(destination), create_blank=True)
    except Exception as exc:
        raise QSpiceError(
            f"Failed to create a starter schematic at {destination.name} "
            f"using {backend_name}.QschEditor."
        ) from exc

    bootstrap_blank_schematic(editor)
    add_simple_component(
        editor,
        component_kind="voltage_source",
        reference=source_reference,
        value=source_value,
        position=_STARTER_SOURCE_POSITION,
    )
    add_simple_component(
        editor,
        component_kind="resistor",
        reference=load_reference,
        value=load_value,
        position=_STARTER_LOAD_POSITION,
    )
    add_wire(
        editor,
        start_reference=source_reference,
        start_pin="+",
        end_reference=load_reference,
        end_pin="1",
        net_name=input_net_name,
    )
    add_simple_component(
        editor,
        component_kind="ground",
        reference=None,
        value=None,
        position=resolve_component_pin_position(editor, reference=load_reference, pin_name="2"),
    )
    add_simple_component(
        editor,
        component_kind="ground",
        reference=None,
        value=None,
        position=resolve_component_pin_position(editor, reference=source_reference, pin_name="-"),
    )
    add_net_label(
        editor,
        net_name=input_net_name,
        position=resolve_component_pin_position(editor, reference=source_reference, pin_name="+"),
    )
    editor.add_instruction(analysis_instruction)
    saved_path = save_editor_as(
        editor,
        workspace_root=workspace_root,
        output_path=destination,
        default=destination,
    )
    return CreatedStarterSchematic(
        output_path=saved_path,
        overwritten=existed,
        source_reference=source_reference,
        source_value=str(source_value),
        load_reference=load_reference,
        load_value=str(load_value),
        input_net_name=input_net_name,
        analysis_instruction=analysis_instruction,
    )


__all__ = ["SERVICE_SPEC", "CreatedStarterSchematic", "create_starter_schematic"]
