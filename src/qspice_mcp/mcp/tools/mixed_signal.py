"""Mixed-signal custom-device scaffold tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from qspice_mcp.services.mixed_signal.build_dll_device import (
    Toolchain,
)
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

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

MIXED_SIGNAL_HANDLER_NAMES = (
    "build_dll_device",
    "describe_mixed_signal_support",
    "validate_dll_symbol_signature",
    "scaffold_dll_device",
    "scaffold_dll_device_from_symbol",
    "scaffold_verilog_device",
    "scaffold_socket_device",
    "scaffold_python_device",
)


class MixedSignalToolMixin:
    """Handlers for mixed-signal custom-device scaffold tools."""

    def build_dll_device(
        self: _RuntimeWithSettings,
        source_path: str,
        output_path: str | None = None,
        toolchain: str = "auto",
        timeout_s: float | None = 120.0,
    ) -> dict[str, object]:
        build = build_dll_device_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
            toolchain=cast("Toolchain", toolchain),
            timeout_s=timeout_s,
            qspice_executable=self.settings.exe,
        )
        return to_json_object(build)

    def describe_mixed_signal_support(self: _RuntimeWithSettings) -> dict[str, object]:
        inspection = describe_mixed_signal_support_service(settings=self.settings)
        return to_json_object(inspection)

    def validate_dll_symbol_signature(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        source_path: str,
    ) -> dict[str, object]:
        validation = validate_dll_symbol_signature_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            source_path=source_path,
        )
        return to_json_object(validation)

    def scaffold_dll_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_dir: str | None = None,
        schematic_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_dll_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_dir=output_dir,
            schematic_path=schematic_path,
        )
        return to_json_object(scaffold)

    def scaffold_dll_device_from_symbol(
        self: _RuntimeWithSettings,
        schematic_path: str,
        reference: str,
        output_dir: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_dll_device_from_symbol_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            reference=reference,
            output_dir=output_dir,
        )
        return to_json_object(scaffold)

    def scaffold_verilog_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_verilog_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(scaffold)

    def scaffold_socket_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_socket_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(scaffold)

    def scaffold_python_device(
        self: _RuntimeWithSettings,
        device_name: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_python_device_service(
            device_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(scaffold)


__all__ = [
    "MIXED_SIGNAL_HANDLER_NAMES",
    "MixedSignalToolMixin",
    "validate_dll_symbol_signature_service",
]
