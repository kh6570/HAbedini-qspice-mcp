"""Protocol co-simulation scaffold tool handlers."""

from __future__ import annotations

from qspice_mcp.services.protocol.describe_protocol_support import (
    describe_protocol_support as describe_protocol_support_service,
)
from qspice_mcp.services.protocol.scaffold_i2c_device import (
    scaffold_i2c_device as scaffold_i2c_device_service,
)
from qspice_mcp.services.protocol.scaffold_spi_device import (
    scaffold_spi_device as scaffold_spi_device_service,
)

__all__ = [
    "describe_protocol_support_service",
    "scaffold_i2c_device_service",
    "scaffold_spi_device_service",
]
