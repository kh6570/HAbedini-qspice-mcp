"""Subcircuit tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.subcircuit.list_subcircuits import (
    list_subcircuits as list_subcircuits_service,
)
from qspice_mcp.services.subcircuit.read_subcircuit import (
    read_subcircuit as read_subcircuit_service,
)
from qspice_mcp.services.subcircuit.set_subcircuit_component_parameters import (
    set_subcircuit_component_parameters as set_subcircuit_component_parameters_service,
)
from qspice_mcp.services.subcircuit.set_subcircuit_component_value import (
    set_subcircuit_component_value as set_subcircuit_component_value_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

SubcircuitScope = Literal["instance", "definition"]

SUBCIRCUIT_HANDLER_NAMES = (
    "list_subcircuits",
    "read_subcircuit",
    "set_subcircuit_component_value",
    "set_subcircuit_component_parameters",
)


class SubcircuitToolMixin:
    """Handlers for subcircuit inspection and edit tools."""

    def list_subcircuits(
        self: _RuntimeWithSettings,
        schematic_path: str,
        instance_path: list[str] | None = None,
    ) -> dict[str, object]:
        inspection = list_subcircuits_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            instance_path=instance_path,
        )
        return to_json_object(inspection)

    def read_subcircuit(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        scope: SubcircuitScope = "instance",
        instance_path: list[str] | None = None,
    ) -> dict[str, object]:
        inspection = read_subcircuit_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            scope=scope,
            instance_path=instance_path,
        )
        return to_json_object(inspection)

    def set_subcircuit_component_value(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        component_reference: str,
        value: str | int | float,
        scope: SubcircuitScope = "instance",
        instance_path: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_subcircuit_component_value_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            component_reference=component_reference,
            value=value,
            scope=scope,
            instance_path=instance_path,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def set_subcircuit_component_parameters(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        component_reference: str,
        parameters: dict[str, object],
        scope: SubcircuitScope = "instance",
        instance_path: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = set_subcircuit_component_parameters_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            component_reference=component_reference,
            parameters=parameters,
            scope=scope,
            instance_path=instance_path,
            output_path=output_path,
        )
        return to_json_object(inspection)


__all__ = [
    "SUBCIRCUIT_HANDLER_NAMES",
    "SubcircuitToolMixin",
    "list_subcircuits_service",
    "read_subcircuit_service",
    "set_subcircuit_component_parameters_service",
    "set_subcircuit_component_value_service",
]
