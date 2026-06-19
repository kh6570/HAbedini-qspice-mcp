"""Schematic tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.schematic.add_component import (
    add_component as add_component_service,
)
from qspice_mcp.services.schematic.add_component_symbol_drawing import (
    add_component_symbol_drawing as add_component_symbol_drawing_service,
)
from qspice_mcp.services.schematic.add_dll_block import (
    add_dll_block as add_dll_block_service,
)
from qspice_mcp.services.schematic.add_dll_block_pin import (
    add_dll_block_pin as add_dll_block_pin_service,
)
from qspice_mcp.services.schematic.add_instruction import (
    add_instruction as add_instruction_service,
)
from qspice_mcp.services.schematic.add_junction import (
    add_junction as add_junction_service,
)
from qspice_mcp.services.schematic.add_net_label import (
    add_net_label as add_net_label_service,
)
from qspice_mcp.services.schematic.add_wire import add_wire as add_wire_service
from qspice_mcp.services.schematic.create_schematic import (
    create_schematic as create_schematic_service,
)
from qspice_mcp.services.schematic.create_starter_schematic import (
    create_starter_schematic as create_starter_schematic_service,
)
from qspice_mcp.services.schematic.describe_edit_capability import (
    EditIntent,
)
from qspice_mcp.services.schematic.describe_edit_capability import (
    describe_edit_capability as describe_edit_capability_service,
)
from qspice_mcp.services.schematic.describe_schematic_edit_support import (
    describe_schematic_edit_support as describe_schematic_edit_support_service,
)
from qspice_mcp.services.schematic.import_circuit_bundle import (
    import_circuit_bundle as import_circuit_bundle_service,
)
from qspice_mcp.services.schematic.inspect_schematic import (
    inspect_schematic as inspect_schematic_service,
)
from qspice_mcp.services.schematic.list_components import list_components as list_components_service
from qspice_mcp.services.schematic.materialize_reference_circuit import (
    materialize_reference_circuit as materialize_reference_circuit_service,
)
from qspice_mcp.services.schematic.read_component import read_component as read_component_service
from qspice_mcp.services.schematic.read_component_symbol import (
    read_component_symbol as read_component_symbol_service,
)
from qspice_mcp.services.schematic.remove_component import (
    remove_component as remove_component_service,
)
from qspice_mcp.services.schematic.remove_component_symbol_drawing import (
    remove_component_symbol_drawing as remove_component_symbol_drawing_service,
)
from qspice_mcp.services.schematic.remove_dll_block_pin import (
    remove_dll_block_pin as remove_dll_block_pin_service,
)
from qspice_mcp.services.schematic.remove_instruction import (
    remove_instruction as remove_instruction_service,
)
from qspice_mcp.services.schematic.remove_junction import (
    remove_junction as remove_junction_service,
)
from qspice_mcp.services.schematic.remove_net_label import (
    remove_net_label as remove_net_label_service,
)
from qspice_mcp.services.schematic.remove_wire import remove_wire as remove_wire_service
from qspice_mcp.services.schematic.rename_component_reference import (
    rename_component_reference as rename_component_reference_service,
)
from qspice_mcp.services.schematic.save_schematic_as import (
    save_schematic_as as save_schematic_as_service,
)
from qspice_mcp.services.schematic.set_component_parameters import (
    set_component_parameters as set_component_parameters_service,
)
from qspice_mcp.services.schematic.set_component_position import (
    set_component_position as set_component_position_service,
)
from qspice_mcp.services.schematic.set_component_rotation import (
    set_component_rotation as set_component_rotation_service,
)
from qspice_mcp.services.schematic.set_component_symbol_drawing import (
    set_component_symbol_drawing as set_component_symbol_drawing_service,
)
from qspice_mcp.services.schematic.set_component_symbol_pin import (
    set_component_symbol_pin as set_component_symbol_pin_service,
)
from qspice_mcp.services.schematic.set_component_symbol_text import (
    set_component_symbol_text as set_component_symbol_text_service,
)
from qspice_mcp.services.schematic.set_component_value import (
    set_component_value as set_component_value_service,
)
from qspice_mcp.services.schematic.set_dll_block_pin_role import (
    set_dll_block_pin_role as set_dll_block_pin_role_service,
)
from qspice_mcp.services.schematic.set_element_model import (
    set_element_model as set_element_model_service,
)
from qspice_mcp.services.schematic.set_parameter import set_parameter as set_parameter_service

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

SCHEMATIC_HANDLER_NAMES = (
    "materialize_reference_circuit",
    "import_circuit_bundle",
    "create_schematic",
    "create_starter_schematic",
    "describe_edit_capability",
    "describe_schematic_edit_support",
    "add_component",
    "add_dll_block",
    "add_dll_block_pin",
    "add_component_symbol_drawing",
    "add_wire",
    "remove_wire",
    "remove_net_label",
    "remove_junction",
    "add_junction",
    "add_net_label",
    "inspect_schematic",
    "list_components",
    "read_component",
    "read_component_symbol",
    "save_schematic_as",
    "set_dll_block_pin_role",
    "set_component_symbol_drawing",
    "set_component_symbol_text",
    "set_component_symbol_pin",
    "set_component_position",
    "set_component_rotation",
    "set_component_value",
    "set_component_parameters",
    "set_element_model",
    "set_parameter",
    "add_instruction",
    "remove_dll_block_pin",
    "remove_component",
    "remove_component_symbol_drawing",
    "remove_instruction",
    "rename_component_reference",
)


class SchematicToolMixin:
    """Handlers for schematic inspection and edit tools."""

    def materialize_reference_circuit(
        self: _RuntimeWithSettings,
        recipe_id: str,
        output_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        result = materialize_reference_circuit_service(
            recipe_id,
            workspace_root=self.settings.workspace_root,
            output_dir=output_dir,
            overwrite=overwrite,
        )
        return to_json_object(result)

    def import_circuit_bundle(
        self: _RuntimeWithSettings,
        schematic_path: str,
        output_dir: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, object]:
        result = import_circuit_bundle_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            output_dir=output_dir,
            overwrite=overwrite,
        )
        return to_json_object(result)

    def create_schematic(
        self: _RuntimeWithSettings,
        output_path: str,
        overwrite: bool = False,
    ) -> dict[str, object]:
        inspection = create_schematic_service(
            output_path,
            workspace_root=self.settings.workspace_root,
            overwrite=overwrite,
        )
        return to_json_object(inspection)

    def add_component(
        self: _RuntimeWithSettings,
        schematic_path: str,
        component_kind: str,
        reference: str | None = None,
        value: str | int | float | None = None,
        position_x: int = 0,
        position_y: int = 0,
        rotation_degrees: int = 0,
        net_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_component_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            component_kind=component_kind,
            reference=reference,
            value=value,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            net_name=net_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def add_dll_block(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        device_name: str,
        input_pin_names: list[str] | None = None,
        output_pin_names: list[str] | None = None,
        position_x: int = 0,
        position_y: int = 0,
        rotation_degrees: int = 0,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_dll_block_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            device_name=device_name,
            input_pin_names=("in0",) if input_pin_names is None else input_pin_names,
            output_pin_names=("out0",) if output_pin_names is None else output_pin_names,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def add_dll_block_pin(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        pin_name: str,
        direction: str,
        insert_index: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_dll_block_pin_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            pin_name=pin_name,
            direction=direction,
            insert_index=insert_index,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def add_component_symbol_drawing(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        tag_name: str,
        arguments: list[str],
        insert_index: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_component_symbol_drawing_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            tag_name=tag_name,
            arguments=arguments,
            insert_index=insert_index,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def describe_schematic_edit_support(self: _RuntimeWithSettings) -> dict[str, object]:
        inspection = describe_schematic_edit_support_service()
        return to_json_object(inspection)

    def describe_edit_capability(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        intent: EditIntent,
    ) -> dict[str, object]:
        inspection = describe_edit_capability_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            intent=intent,
        )
        return to_json_object(inspection)

    def create_starter_schematic(
        self: _RuntimeWithSettings,
        output_path: str,
        overwrite: bool = False,
        source_reference: str = "V1",
        source_value: str | int | float = "10",
        load_reference: str = "R1",
        load_value: str | int | float = "1k",
        output_net_name: str = "VOUT",
        analysis_instruction: str = ".op",
    ) -> dict[str, object]:
        inspection = create_starter_schematic_service(
            output_path,
            workspace_root=self.settings.workspace_root,
            overwrite=overwrite,
            source_reference=source_reference,
            source_value=source_value,
            load_reference=load_reference,
            load_value=load_value,
            output_net_name=output_net_name,
            analysis_instruction=analysis_instruction,
        )
        return to_json_object(inspection)

    def add_wire(
        self: _RuntimeWithSettings,
        schematic_path: str,
        *,
        start_x: int | None = None,
        start_y: int | None = None,
        end_x: int | None = None,
        end_y: int | None = None,
        start_reference: str | None = None,
        start_pin: str | None = None,
        end_reference: str | None = None,
        end_pin: str | None = None,
        net_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_wire_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            start_reference=start_reference,
            start_pin=start_pin,
            end_reference=end_reference,
            end_pin=end_pin,
            net_name=net_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_wire(
        self: _RuntimeWithSettings,
        schematic_path: str,
        *,
        start_x: int | None = None,
        start_y: int | None = None,
        end_x: int | None = None,
        end_y: int | None = None,
        start_reference: str | None = None,
        start_pin: str | None = None,
        end_reference: str | None = None,
        end_pin: str | None = None,
        net_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = remove_wire_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            start_reference=start_reference,
            start_pin=start_pin,
            end_reference=end_reference,
            end_pin=end_pin,
            net_name=net_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_net_label(
        self: _RuntimeWithSettings,
        schematic_path: str,
        position_x: int,
        position_y: int,
        *,
        net_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = remove_net_label_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            position_x=position_x,
            position_y=position_y,
            net_name=net_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_junction(
        self: _RuntimeWithSettings,
        schematic_path: str,
        position_x: int,
        position_y: int,
        output_path: str | None = None,
    ) -> dict[str, object]:
        result = remove_junction_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            position_x=position_x,
            position_y=position_y,
            output_path=output_path,
        )
        return to_json_object(result)

    def add_junction(
        self: _RuntimeWithSettings,
        schematic_path: str,
        position_x: int,
        position_y: int,
        output_path: str | None = None,
    ) -> dict[str, object]:
        result = add_junction_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            position_x=position_x,
            position_y=position_y,
            output_path=output_path,
        )
        return to_json_object(result)

    def add_net_label(
        self: _RuntimeWithSettings,
        schematic_path: str,
        position_x: int,
        position_y: int,
        net_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_net_label_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            position_x=position_x,
            position_y=position_y,
            net_name=net_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def inspect_schematic(self: _RuntimeWithSettings, schematic_path: str) -> dict[str, object]:
        inspection = inspect_schematic_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(inspection)

    def list_components(
        self: _RuntimeWithSettings,
        schematic_path: str,
        prefixes: str = "*",
    ) -> dict[str, object]:
        inspection = list_components_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            prefixes=prefixes,
        )
        return to_json_object(inspection)

    def read_component(
        self: _RuntimeWithSettings, schematic_path: str, reference: str
    ) -> dict[str, object]:
        inspection = read_component_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
        )
        return to_json_object(inspection)

    def read_component_symbol(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
    ) -> dict[str, object]:
        inspection = read_component_symbol_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
        )
        return to_json_object(inspection)

    def save_schematic_as(
        self: _RuntimeWithSettings, schematic_path: str, output_path: str
    ) -> dict[str, object]:
        inspection = save_schematic_as_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_value(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        value: str | int | float,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_value_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            value=value,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_position(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        position_x: int,
        position_y: int,
        rotation_degrees: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_position_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_rotation(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        rotation_degrees: int,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_rotation_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            rotation_degrees=rotation_degrees,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_symbol_text(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        text_index: int | None = None,
        text_role: str | None = None,
        text: str | None = None,
        position_x: int | None = None,
        position_y: int | None = None,
        size: int | None = None,
        rotation_code: int | None = None,
        is_comment: bool | None = None,
        color_code: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_symbol_text_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            text_index=text_index,
            text_role=text_role,
            text=text,
            position_x=position_x,
            position_y=position_y,
            size=size,
            rotation_code=rotation_code,
            is_comment=is_comment,
            color_code=color_code,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_symbol_drawing(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        drawing_index: int,
        tag_name: str | None = None,
        arguments: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_symbol_drawing_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            drawing_index=drawing_index,
            tag_name=tag_name,
            arguments=arguments,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_dll_block_pin_role(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        pin_role: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_dll_block_pin_role_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            pin_role=pin_role,
            pin_index=pin_index,
            pin_name=pin_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_symbol_pin(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        new_pin_name: str | None = None,
        label_position_x: int | None = None,
        label_position_y: int | None = None,
        text_size: int | None = None,
        label_anchor_code: int | None = None,
        pin_kind_code: int | None = None,
        color_code: str | None = None,
        aux_code: int | None = None,
        behavioral_net_override: str | None = None,
        clear_behavioral_net_override: bool = False,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_symbol_pin_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            pin_index=pin_index,
            pin_name=pin_name,
            new_pin_name=new_pin_name,
            label_position_x=label_position_x,
            label_position_y=label_position_y,
            text_size=text_size,
            label_anchor_code=label_anchor_code,
            pin_kind_code=pin_kind_code,
            color_code=color_code,
            aux_code=aux_code,
            behavioral_net_override=behavioral_net_override,
            clear_behavioral_net_override=clear_behavioral_net_override,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_component_parameters(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        parameters: dict[str, object],
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_component_parameters_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            parameters=parameters,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_element_model(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        model: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_element_model_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            model=model,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_parameter(
        self: _RuntimeWithSettings,
        schematic_path: str,
        name: str,
        value: str | int | float,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_parameter_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            name=name,
            value=value,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def add_instruction(
        self: _RuntimeWithSettings,
        schematic_path: str,
        instruction: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = add_instruction_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            instruction=instruction,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_component(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = remove_component_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_component_symbol_drawing(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        drawing_index: int,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = remove_component_symbol_drawing_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            drawing_index=drawing_index,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_dll_block_pin(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = remove_dll_block_pin_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            pin_index=pin_index,
            pin_name=pin_name,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def rename_component_reference(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        new_reference: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = rename_component_reference_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            new_reference=new_reference,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def remove_instruction(
        self: _RuntimeWithSettings,
        schematic_path: str,
        instruction: str,
        output_path: str | None = None,
        regex: bool = False,
    ) -> dict[str, object]:
        inspection = remove_instruction_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            instruction=instruction,
            output_path=output_path,
            regex=regex,
        )
        return to_json_object(inspection)


__all__ = [
    "SCHEMATIC_HANDLER_NAMES",
    "SchematicToolMixin",
    "add_component_service",
    "add_component_symbol_drawing_service",
    "add_dll_block_pin_service",
    "add_dll_block_service",
    "add_instruction_service",
    "add_net_label_service",
    "add_wire_service",
    "create_schematic_service",
    "create_starter_schematic_service",
    "describe_edit_capability_service",
    "describe_schematic_edit_support_service",
    "inspect_schematic_service",
    "list_components_service",
    "read_component_service",
    "read_component_symbol_service",
    "remove_component_service",
    "remove_component_symbol_drawing_service",
    "remove_dll_block_pin_service",
    "remove_instruction_service",
    "rename_component_reference_service",
    "save_schematic_as_service",
    "set_component_parameters_service",
    "set_component_position_service",
    "set_component_rotation_service",
    "set_component_symbol_drawing_service",
    "set_component_symbol_pin_service",
    "set_component_symbol_text_service",
    "set_component_value_service",
    "set_dll_block_pin_role_service",
    "set_element_model_service",
    "set_parameter_service",
]
