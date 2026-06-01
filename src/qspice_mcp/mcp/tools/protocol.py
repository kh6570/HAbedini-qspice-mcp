"""Protocol co-simulation scaffold tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.protocol.describe_protocol_support import (
    describe_protocol_support as describe_protocol_support_service,
)
from qspice_mcp.services.protocol.scaffold_i2c_device import (
    scaffold_i2c_device as scaffold_i2c_device_service,
)
from qspice_mcp.services.protocol.scaffold_spi_device import (
    scaffold_spi_device as scaffold_spi_device_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

PROTOCOL_HANDLER_NAMES = (
    "describe_protocol_support",
    "scaffold_i2c_device",
    "scaffold_spi_device",
)


class ProtocolToolMixin:
    """Handlers for protocol co-simulation scaffold tools."""

    def describe_protocol_support(self: _RuntimeWithSettings) -> dict[str, object]:
        inspection = describe_protocol_support_service(settings=self.settings)
        return to_json_object(inspection)

    def scaffold_i2c_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_i2c_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(scaffold)

    def scaffold_spi_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_spi_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(scaffold)


__all__ = ["PROTOCOL_HANDLER_NAMES", "ProtocolToolMixin"]
