"""Service describing protocol co-simulation tooling state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class ProtocolSupport:
    """Reported protocol co-simulation scaffolding capability."""

    i2c_device_scaffolding: bool
    spi_device_scaffolding: bool
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="describe_protocol_support",
    title="Describe Protocol Support",
    summary=("Describe which protocol co-simulation scaffold generators (I2C, SPI) are available."),
    phase="implemented",
)


def describe_protocol_support(*, settings: QSpiceSettings) -> ProtocolSupport:
    """Describe the available protocol co-simulation scaffolding surface."""

    del settings
    return ProtocolSupport(
        i2c_device_scaffolding=True,
        spi_device_scaffolding=True,
        notes=(
            "All protocol scaffold generators are available. "
            "Use scaffold_i2c_device or scaffold_spi_device to generate "
            "a C++ DLL project that uses QSpice's built-in I2C/SPI helper "
            "functions for bus-level co-simulation.",
        ),
    )


__all__ = ["SERVICE_SPEC", "ProtocolSupport", "describe_protocol_support"]
