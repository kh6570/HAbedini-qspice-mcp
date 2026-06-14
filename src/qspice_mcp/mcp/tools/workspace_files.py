"""Workspace file and topology-capability tool handlers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.services.instructions.list_workflow_instructions import (
    list_workflow_instructions as list_workflow_instructions_service,
)
from qspice_mcp.services.instructions.read_workflow_instruction import (
    read_workflow_instruction as read_workflow_instruction_service,
)
from qspice_mcp.services.mixed_signal.build_dll_device import (
    build_dll_device as build_dll_device_service,
)
from qspice_mcp.services.mixed_signal.validate_dll_symbol_signature import (
    validate_dll_symbol_signature as validate_dll_symbol_signature_service,
)
from qspice_mcp.services.schematic.describe_topology_authoring_support import (
    describe_topology_authoring_support as describe_topology_authoring_support_service,
)
from qspice_mcp.services.workspace.write_workspace_text_file import (
    write_workspace_text_file as write_workspace_text_file_service,
)

from .shared import to_json_object

_DLL_SOURCE_SUFFIXES = frozenset({".c", ".cc", ".cpp", ".cxx"})

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

WORKSPACE_FILES_HANDLER_NAMES = (
    "write_workspace_text_file",
    "describe_topology_authoring_support",
    "list_workflow_instructions",
    "read_workflow_instruction",
)


class WorkspaceFilesToolMixin:
    """Handlers for workspace text writes and topology capability discovery."""

    def write_workspace_text_file(
        self: _RuntimeWithSettings,
        relative_path: str,
        content: str,
        overwrite: bool = False,
        build_dll_after_write: bool | None = None,
        schematic_path: str | None = None,
        dll_reference: str | None = None,
        dll_toolchain: str = "auto",
        dll_timeout_s: float | None = 120.0,
    ) -> dict[str, object]:
        result = write_workspace_text_file_service(
            relative_path,
            workspace_root=self.settings.workspace_root,
            content=content,
            overwrite=overwrite,
        )
        payload = to_json_object(result)
        suffix = Path(relative_path).suffix.lower()
        should_build_dll = (
            suffix in _DLL_SOURCE_SUFFIXES
            if build_dll_after_write is None
            else build_dll_after_write
        )
        if not should_build_dll or suffix not in _DLL_SOURCE_SUFFIXES:
            return payload

        dll_path = result.output_path.with_suffix(".dll")

        def _record_existing_dll(*, note: str | None = None) -> None:
            entry: dict[str, object] = {
                "source_path": str(result.output_path),
                "output_path": str(dll_path),
                "toolchain": "existing",
                "skipped_rebuild": True,
            }
            if note is not None:
                entry["note"] = note
            payload["dll_build"] = entry

        if dll_path.is_file():
            _record_existing_dll()
        else:
            try:
                build = build_dll_device_service(
                    result.output_path.name,
                    workspace_root=self.settings.workspace_root,
                    toolchain=dll_toolchain,  # type: ignore[arg-type]
                    timeout_s=dll_timeout_s,
                    qspice_executable=self.settings.exe,
                )
            except (BackendUnavailableError, ValidationError) as exc:
                if dll_path.is_file():
                    _record_existing_dll(note=str(exc))
                else:
                    payload["dll_build_error"] = str(exc)
                    return payload
            else:
                payload["dll_build"] = to_json_object(build)

        if schematic_path is not None and dll_reference is not None:
            validation = validate_dll_symbol_signature_service(
                schematic_path,
                workspace_root=self.settings.workspace_root,
                reference=dll_reference,
                source_path=result.output_path.name,
            )
            payload["dll_validation"] = to_json_object(validation)
            if not validation.is_valid:
                mismatches = ", ".join(validation.mismatches)
                raise ValidationError(
                    f"DLL symbol validation failed for {dll_reference}: {mismatches}"
                )

        return payload

    def describe_topology_authoring_support(self: _RuntimeWithSettings) -> dict[str, object]:
        result = describe_topology_authoring_support_service()
        return to_json_object(result)

    def list_workflow_instructions(self: _RuntimeWithSettings) -> dict[str, object]:
        result = list_workflow_instructions_service()
        return to_json_object(result)

    def read_workflow_instruction(
        self: _RuntimeWithSettings,
        instruction_id: str,
    ) -> dict[str, object]:
        result = read_workflow_instruction_service(instruction_id)
        return to_json_object(result)


__all__ = ["WORKSPACE_FILES_HANDLER_NAMES", "WorkspaceFilesToolMixin"]
