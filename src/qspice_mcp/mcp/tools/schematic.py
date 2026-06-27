"""Schematic tool handlers."""

from __future__ import annotations

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

__all__ = [
    "add_component_service",
    "add_component_symbol_drawing_service",
    "add_dll_block_pin_service",
    "add_dll_block_service",
    "add_instruction_service",
    "add_junction_service",
    "add_net_label_service",
    "add_wire_service",
    "create_schematic_service",
    "create_starter_schematic_service",
    "describe_edit_capability_service",
    "describe_schematic_edit_support_service",
    "import_circuit_bundle_service",
    "inspect_schematic_service",
    "list_components_service",
    "materialize_reference_circuit_service",
    "read_component_service",
    "read_component_symbol_service",
    "remove_component_service",
    "remove_component_symbol_drawing_service",
    "remove_dll_block_pin_service",
    "remove_instruction_service",
    "remove_junction_service",
    "remove_net_label_service",
    "remove_wire_service",
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
