"""Declarative MCP tool handler bindings derived from the service catalog."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.services._internals.service_catalog import build_service_callable_catalog
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.mixed_signal._dll_toolchain_probe import dll_build_degradation_hints

from ._service_lookup import resolve_mcp_service_callable
from .shared import to_json_object

if TYPE_CHECKING:
    from qspice_mcp.mcp.tool_registry import ToolDefinition
    from qspice_mcp.services.mixed_signal.build_dll_device import Toolchain
    from qspice_mcp.services.mixed_signal.validate_dll_symbol_signature import (
        DllSymbolSignatureValidation,
    )
    from qspice_mcp.services.simulation._netlist_result import GeneratedNetlist
    from qspice_mcp.services.workspace.write_workspace_text_file import (
        WrittenWorkspaceTextFile,
    )

    from .runtime import QSpiceToolRuntime

ToolHandler = Callable[..., dict[str, object]]

_DLL_SOURCE_SUFFIXES = frozenset({".c", ".cc", ".cpp", ".cxx"})
_BATCH_TOOL_NAMES = frozenset(
    {"cancel_batch", "collect_batch_results", "get_batch_status", "submit_batch"}
)
_REMOTE_TOOL_NAMES = frozenset(
    {
        "close_remote_session",
        "download_remote_artifacts",
        "poll_remote_run",
        "submit_remote_simulation",
    }
)
_LIVE_GUI_SESSION_TOOL_NAMES = frozenset(
    {
        "close_live_gui_session",
        "launch_live_gui_session",
        "poll_live_gui_session",
        "poll_live_gui_session_events",
        "send_live_gui_session_command",
    }
)
_SPECIAL_TOOL_NAMES = frozenset(
    {
        "add_dll_block",
        "describe_server_capabilities",
        "run_simulation",
        "write_workspace_text_file",
    }
)


def _normalize_tool_kwargs(name: str, kwargs: dict[str, object]) -> dict[str, object]:
    normalized = dict(kwargs)
    if "extra_switches" in normalized and normalized["extra_switches"] is not None:
        normalized["extra_switches"] = tuple(cast("list[str]", normalized["extra_switches"]))
    if name == "add_dll_block":
        if normalized.get("input_pin_names") is None:
            normalized["input_pin_names"] = ("in0",)
        if normalized.get("output_pin_names") is None:
            normalized["output_pin_names"] = ("out0",)
    return normalized


def _build_service_call_kwargs(
    runtime: QSpiceToolRuntime,
    service_fn: Callable[..., object],
    tool_kwargs: dict[str, object],
) -> dict[str, object]:
    call_kwargs: dict[str, object] = {}
    for name, parameter in inspect.signature(service_fn).parameters.items():
        if name == "workspace_root":
            call_kwargs[name] = runtime.settings.workspace_root
        elif name == "settings":
            call_kwargs[name] = runtime.settings
        elif name == "qspice_executable":
            call_kwargs[name] = runtime.settings.exe
        elif name in tool_kwargs:
            call_kwargs[name] = tool_kwargs[name]
        elif parameter.default is not inspect.Parameter.empty or parameter.kind in (
            inspect.Parameter.VAR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        ):
            continue
        else:
            raise TypeError(
                f"Missing required tool argument {name!r} for service {service_fn.__name__}."
            )
    return call_kwargs


def _make_service_handler(
    runtime: QSpiceToolRuntime,
    *,
    tool_name: str,
) -> ToolHandler:
    def handler(**kwargs: object) -> dict[str, object]:
        service_fn = resolve_mcp_service_callable(tool_name)
        normalized = _normalize_tool_kwargs(tool_name, dict(kwargs))
        call_kwargs = _build_service_call_kwargs(runtime, service_fn, normalized)
        return to_json_object(service_fn(**call_kwargs))

    handler.__name__ = tool_name
    return handler


def _describe_server_capabilities_handler(runtime: QSpiceToolRuntime) -> ToolHandler:
    def handler() -> dict[str, object]:
        describe_server_capabilities_runtime = resolve_mcp_service_callable(
            "describe_server_capabilities"
        )
        return to_json_object(
            describe_server_capabilities_runtime(settings=runtime.settings, tools=runtime.tools)
        )

    handler.__name__ = "describe_server_capabilities"
    return handler


def _run_simulation_handler(runtime: QSpiceToolRuntime) -> ToolHandler:
    def handler(
        source_path: str,
        dry_run: bool = False,
        timeout_s: float | None = None,
        log_path: str | None = None,
        raw_output_path: str | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        netlist_output_path: str | None = None,
    ) -> dict[str, object]:
        resolved_source = resolve_workspace_path(
            source_path, workspace_root=runtime.settings.workspace_root
        )
        generated_netlist: dict[str, object] | None = None
        warnings: list[str] = []
        simulation_input = resolved_source

        if resolved_source.suffix.lower() == ".qsch":
            generate_netlist_service = resolve_mcp_service_callable("generate_netlist")
            generated = cast(
                "GeneratedNetlist",
                generate_netlist_service(
                    resolved_source,
                    workspace_root=runtime.settings.workspace_root,
                    output_path=netlist_output_path,
                    settings=runtime.settings,
                ),
            )
            generated_netlist = to_json_object(generated)
            warnings.extend(str(item) for item in generated.warnings)
            simulation_input = generated.netlist_path
        elif netlist_output_path is not None:
            warnings.append(
                "netlist_output_path is ignored when source_path already points "
                "to a .net or .cir file."
            )

        run_simulation_service = resolve_mcp_service_callable("run_simulation")
        result = run_simulation_service(
            simulation_input,
            workspace_root=runtime.settings.workspace_root,
            settings=runtime.settings,
            dry_run=dry_run,
            timeout_s=timeout_s,
            log_path=log_path,
            raw_output_path=raw_output_path,
            extra_switches=tuple(extra_switches or ()),
            ascii_raw=ascii_raw,
        )
        payload = to_json_object(result)
        payload["source_path"] = str(resolved_source)
        if generated_netlist is not None:
            payload["generated_netlist"] = generated_netlist
        if warnings:
            payload["warnings"] = warnings
        return payload

    handler.__name__ = "run_simulation"
    return handler


def _write_workspace_text_file_handler(runtime: QSpiceToolRuntime) -> ToolHandler:
    def handler(
        relative_path: str,
        content: str,
        overwrite: bool = False,
        build_dll_after_write: bool | None = None,
        schematic_path: str | None = None,
        dll_reference: str | None = None,
        dll_toolchain: str = "auto",
        dll_timeout_s: float | None = 120.0,
    ) -> dict[str, object]:
        write_workspace_text_file_service = resolve_mcp_service_callable(
            "write_workspace_text_file"
        )
        result = cast(
            "WrittenWorkspaceTextFile",
            write_workspace_text_file_service(
                relative_path,
                workspace_root=runtime.settings.workspace_root,
                content=content,
                overwrite=overwrite,
            ),
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
                build_dll_device_service = resolve_mcp_service_callable("build_dll_device")
                build = build_dll_device_service(
                    result.output_path.name,
                    workspace_root=runtime.settings.workspace_root,
                    toolchain=cast("Toolchain", dll_toolchain),
                    timeout_s=dll_timeout_s,
                    qspice_executable=runtime.settings.exe,
                )
            except (BackendUnavailableError, ValidationError) as exc:
                if dll_path.is_file():
                    _record_existing_dll(note=str(exc))
                else:
                    payload["dll_build_error"] = str(exc)
                    payload["dll_build_hints"] = dll_build_degradation_hints(
                        qspice_executable=runtime.settings.exe,
                        error=str(exc),
                    )
                    return payload
            else:
                payload["dll_build"] = to_json_object(build)

        if schematic_path is not None and dll_reference is not None:
            validate_dll_symbol_signature_service = resolve_mcp_service_callable(
                "validate_dll_symbol_signature"
            )
            validation = cast(
                "DllSymbolSignatureValidation",
                validate_dll_symbol_signature_service(
                    schematic_path,
                    workspace_root=runtime.settings.workspace_root,
                    reference=dll_reference,
                    source_path=result.output_path.name,
                ),
            )
            payload["dll_validation"] = to_json_object(validation)
            if not validation.is_valid:
                mismatches = ", ".join(validation.mismatches)
                raise ValidationError(
                    f"DLL symbol validation failed for {dll_reference}: {mismatches}"
                )

        return payload

    handler.__name__ = "write_workspace_text_file"
    return handler


def _make_manager_handler(runtime: QSpiceToolRuntime, tool_name: str) -> ToolHandler:
    if tool_name in _BATCH_TOOL_NAMES:
        manager: object = runtime._batch_manager
    elif tool_name in _REMOTE_TOOL_NAMES:
        manager = runtime._remote_manager
    elif tool_name in _LIVE_GUI_SESSION_TOOL_NAMES:
        manager = runtime._live_gui_manager
    else:
        raise KeyError(f"No manager binding registered for {tool_name!r}.")

    method = cast("Callable[..., object]", getattr(manager, tool_name))

    def handler(**kwargs: object) -> dict[str, object]:
        normalized = _normalize_tool_kwargs(tool_name, dict(kwargs))
        return to_json_object(method(**normalized))

    handler.__name__ = tool_name
    return handler


def _build_special_handler(runtime: QSpiceToolRuntime, tool_name: str) -> ToolHandler:
    if tool_name == "describe_server_capabilities":
        return _describe_server_capabilities_handler(runtime)
    if tool_name == "run_simulation":
        return _run_simulation_handler(runtime)
    if tool_name == "write_workspace_text_file":
        return _write_workspace_text_file_handler(runtime)
    if tool_name == "add_dll_block":
        return _make_service_handler(runtime, tool_name=tool_name)
    raise KeyError(f"No special handler registered for {tool_name!r}.")


def build_raw_tool_handlers(
    runtime: QSpiceToolRuntime,
    tools: tuple[ToolDefinition, ...],
) -> dict[str, ToolHandler]:
    """Build unwrapped MCP handlers from the service catalog and runtime context."""

    service_catalog = build_service_callable_catalog()
    handlers: dict[str, ToolHandler] = {}
    for tool in tools:
        name = tool.name
        if name in _SPECIAL_TOOL_NAMES:
            handlers[name] = _build_special_handler(runtime, name)
        elif name in _BATCH_TOOL_NAMES | _REMOTE_TOOL_NAMES | _LIVE_GUI_SESSION_TOOL_NAMES:
            handlers[name] = _make_manager_handler(runtime, name)
        elif name in service_catalog:
            handlers[name] = _make_service_handler(runtime, tool_name=name)
        else:
            raise RuntimeError(f"No handler binding found for implemented tool {name!r}.")
    return handlers


__all__ = ["ToolHandler", "build_raw_tool_handlers"]
