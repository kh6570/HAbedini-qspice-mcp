"""Service describing mixed-signal custom-device tooling state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class MixedSignalSupport:
    """Reported mixed-signal custom-device scaffolding capability."""

    dll_device_scaffolding: bool
    verilog_device_scaffolding: bool
    socket_device_scaffolding: bool
    python_device_scaffolding: bool
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="describe_mixed_signal_support",
    title="Describe Mixed-Signal Support",
    summary=(
        "Describe which mixed-signal custom-device scaffold generators "
        "(.DLL, Verilog, socket, Python) are available."
    ),
    phase="implemented",
)


def describe_mixed_signal_support(*, settings: QSpiceSettings) -> MixedSignalSupport:
    """Describe the available mixed-signal scaffolding surface."""

    del settings
    return MixedSignalSupport(
        dll_device_scaffolding=True,
        verilog_device_scaffolding=True,
        socket_device_scaffolding=True,
        python_device_scaffolding=True,
        notes=(
            "All mixed-signal scaffold generators are available. "
            "Use scaffold_dll_device, scaffold_verilog_device, "
            "scaffold_socket_device, or scaffold_python_device to generate "
            "a template project for the desired custom-device workflow.",
            "For .DLL devices prefer create_dll_device_from_spec (one call from a "
            "PinDef-style pin spec; see describe_device_spec) or "
            "scaffold_dll_device_from_symbol (source stub from an already placed "
            "block).",
        ),
    )


__all__ = ["SERVICE_SPEC", "MixedSignalSupport", "describe_mixed_signal_support"]
