"""Mixed-signal custom-device scaffolding services for QSPICE."""

from __future__ import annotations

from .describe_mixed_signal_support import (
    SERVICE_SPEC as DESCRIBE_MIXED_SIGNAL_SUPPORT_SERVICE,
)
from .describe_mixed_signal_support import (
    MixedSignalSupport,
    describe_mixed_signal_support,
)
from .scaffold_dll_device import SERVICE_SPEC as SCAFFOLD_DLL_DEVICE_SERVICE
from .scaffold_dll_device import DllDeviceScaffold, scaffold_dll_device
from .scaffold_python_device import SERVICE_SPEC as SCAFFOLD_PYTHON_DEVICE_SERVICE
from .scaffold_python_device import PythonDeviceScaffold, scaffold_python_device
from .scaffold_socket_device import SERVICE_SPEC as SCAFFOLD_SOCKET_DEVICE_SERVICE
from .scaffold_socket_device import SocketDeviceScaffold, scaffold_socket_device
from .scaffold_verilog_device import SERVICE_SPEC as SCAFFOLD_VERILOG_DEVICE_SERVICE
from .scaffold_verilog_device import VerilogDeviceScaffold, scaffold_verilog_device

__all__ = [
    "DESCRIBE_MIXED_SIGNAL_SUPPORT_SERVICE",
    "SCAFFOLD_DLL_DEVICE_SERVICE",
    "SCAFFOLD_PYTHON_DEVICE_SERVICE",
    "SCAFFOLD_SOCKET_DEVICE_SERVICE",
    "SCAFFOLD_VERILOG_DEVICE_SERVICE",
    "DllDeviceScaffold",
    "MixedSignalSupport",
    "PythonDeviceScaffold",
    "SocketDeviceScaffold",
    "VerilogDeviceScaffold",
    "describe_mixed_signal_support",
    "scaffold_dll_device",
    "scaffold_python_device",
    "scaffold_socket_device",
    "scaffold_verilog_device",
]
