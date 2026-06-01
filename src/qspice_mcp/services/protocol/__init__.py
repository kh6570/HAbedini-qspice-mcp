"""Protocol co-simulation scaffolding services for QSPICE."""

from __future__ import annotations

from .describe_protocol_support import (
    SERVICE_SPEC as DESCRIBE_PROTOCOL_SUPPORT_SERVICE,
)
from .describe_protocol_support import (
    ProtocolSupport,
    describe_protocol_support,
)
from .scaffold_i2c_device import SERVICE_SPEC as SCAFFOLD_I2C_DEVICE_SERVICE
from .scaffold_i2c_device import I2cDeviceScaffold, scaffold_i2c_device
from .scaffold_spi_device import SERVICE_SPEC as SCAFFOLD_SPI_DEVICE_SERVICE
from .scaffold_spi_device import SpiDeviceScaffold, scaffold_spi_device

__all__ = [
    "DESCRIBE_PROTOCOL_SUPPORT_SERVICE",
    "SCAFFOLD_I2C_DEVICE_SERVICE",
    "SCAFFOLD_SPI_DEVICE_SERVICE",
    "I2cDeviceScaffold",
    "ProtocolSupport",
    "SpiDeviceScaffold",
    "describe_protocol_support",
    "scaffold_i2c_device",
    "scaffold_spi_device",
]
