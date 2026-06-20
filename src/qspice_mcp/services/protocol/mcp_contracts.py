"""MCP input schemas and descriptions for this service package."""

from __future__ import annotations

MCP_CONTRACTS: dict[str, dict[str, object]] = {
    "describe_protocol_support": {
        "title": "Describe Protocol Support",
        "description": "Describe which protocol co-simulation scaffold generators (I2C, SPI) are available.",
        "input_schema": {"type": "object", "properties": {}},
    },
    "scaffold_i2c_device": {
        "title": "Scaffold I2C Device",
        "description": "Generate a C++ DLL scaffold that uses QSpice's built-in I2C bus helper functions (qspice_i2c_read, qspice_i2c_write, qspice_i2c_start, qspice_i2c_stop, qspice_i2c_ack, qspice_i2c_nack) for protocol-level co-simulation.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {"device_name": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
    "scaffold_spi_device": {
        "title": "Scaffold SPI Device",
        "description": "Generate a C++ DLL scaffold that uses QSpice's built-in SPI bus helper functions (qspice_spi_read, qspice_spi_write) for protocol-level co-simulation with configurable SPI mode.",
        "input_schema": {
            "type": "object",
            "required": ["device_name"],
            "properties": {"device_name": {"type": "string"}, "output_path": {"type": "string"}},
        },
    },
}
