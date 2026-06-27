"""Mixed-signal custom-device scaffold tool handlers."""

from __future__ import annotations

from qspice_mcp.services.mixed_signal.build_dll_device import (
    build_dll_device as build_dll_device_service,
)
from qspice_mcp.services.mixed_signal.describe_mixed_signal_support import (
    describe_mixed_signal_support as describe_mixed_signal_support_service,
)
from qspice_mcp.services.mixed_signal.scaffold_dll_device import (
    scaffold_dll_device as scaffold_dll_device_service,
)
from qspice_mcp.services.mixed_signal.scaffold_dll_device_from_symbol import (
    scaffold_dll_device_from_symbol as scaffold_dll_device_from_symbol_service,
)
from qspice_mcp.services.mixed_signal.scaffold_python_device import (
    scaffold_python_device as scaffold_python_device_service,
)
from qspice_mcp.services.mixed_signal.scaffold_socket_device import (
    scaffold_socket_device as scaffold_socket_device_service,
)
from qspice_mcp.services.mixed_signal.scaffold_verilog_device import (
    scaffold_verilog_device as scaffold_verilog_device_service,
)
from qspice_mcp.services.mixed_signal.validate_dll_symbol_signature import (
    validate_dll_symbol_signature as validate_dll_symbol_signature_service,
)

__all__ = [
    "build_dll_device_service",
    "describe_mixed_signal_support_service",
    "scaffold_dll_device_from_symbol_service",
    "scaffold_dll_device_service",
    "scaffold_python_device_service",
    "scaffold_socket_device_service",
    "scaffold_verilog_device_service",
    "validate_dll_symbol_signature_service",
]
