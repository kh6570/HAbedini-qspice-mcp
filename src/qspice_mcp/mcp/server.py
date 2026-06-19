"""FastMCP-backed server bootstrap and runtime wiring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, cast

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.exceptions import McpError, UrlElicitationRequiredError
from mcp.types import ContentBlock, ErrorData
from mcp.types import ToolAnnotations as MCPToolAnnotations

from qspice_mcp.adapters import describe_adapters, select_adapter
from qspice_mcp.adapters.probe import ProbeResult, probe_qspice
from qspice_mcp.core.exceptions import (
    AdapterNotFoundError,
    ParseError,
    QSpiceError,
    SimulationError,
)
from qspice_mcp.infra.child_processes import install_shutdown_hooks
from qspice_mcp.infra.config import QSpiceSettings, build_settings
from qspice_mcp.infra.logging import get_logger
from qspice_mcp.infra.progress import bind_context, reset_context
from qspice_mcp.infra.telemetry import get_exception_trace_id

from .definition import ServerDefinition, build_server_definition
from .prompts import get_prompt_definitions
from .prompts.registration import register_prompts
from .resources import ResourceDefinition, get_resource_content, get_resource_definitions
from .tool_registry import (
    ToolAnnotations,
    ToolDefinition,
    build_runtime_tool_registry,
    build_tool_registry,
    build_tool_registry_from_runtime,
)
from .tools import QSpiceToolRuntime
from .tools.workspace import (
    reset_pending_workspace_root,
    resolve_workspace_override,
    set_pending_workspace_root,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from qspice_mcp.adapters.base import AdapterDescription

_QSPICE_TOOL_ERROR_CODE = 0


def _resolve_mcp_log_level(
    level: Literal["debug", "info", "warning", "error"],
) -> Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    """Map app log levels onto the literal set expected by FastMCP."""

    if level == "debug":
        return "DEBUG"
    if level == "info":
        return "INFO"
    if level == "warning":
        return "WARNING"
    return "ERROR"


def _to_mcp_annotations(annotations: ToolAnnotations) -> MCPToolAnnotations:
    """Translate local tool annotations into MCP SDK annotations."""

    return MCPToolAnnotations(
        readOnlyHint=annotations.read_only_hint,
        destructiveHint=annotations.destructive_hint,
        idempotentHint=annotations.idempotent_hint,
        openWorldHint=annotations.open_world_hint,
    )


def _register_resources(app: FastMCP, resources: tuple[ResourceDefinition, ...]) -> None:
    """Register static resource content with the MCP app."""

    def make_resource(body: str) -> Callable[[], str]:
        def resource() -> str:
            return body

        return resource

    for resource in resources:
        body = get_resource_content(resource.uri) or resource.description
        app.resource(
            resource.uri,
            name=resource.name,
            title=resource.name,
            description=resource.description,
            mime_type=resource.mime_type,
        )(make_resource(body))


def _to_mcp_error_data(error: QSpiceError) -> ErrorData:
    """Convert one domain error into a structured MCP error payload."""

    data: dict[str, object] = {
        "error_code": error.error_code,
        "error_type": type(error).__name__,
    }
    trace_id = get_exception_trace_id(error)
    if trace_id is not None:
        data["trace_id"] = trace_id
    if isinstance(error, SimulationError):
        if error.exit_code is not None:
            data["exit_code"] = error.exit_code
        if error.stderr is not None:
            data["stderr"] = error.stderr
    if isinstance(error, ParseError):
        if error.line is not None:
            data["line"] = error.line
        if error.column is not None:
            data["column"] = error.column
    return ErrorData(code=_QSPICE_TOOL_ERROR_CODE, message=str(error), data=data)


class _QSpiceFastMCP(FastMCP):
    """FastMCP variant that preserves structured qspice tool errors."""

    def __init__(
        self, *args: Any, tool_runtime: QSpiceToolRuntime | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._tool_runtime = tool_runtime

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> list[ContentBlock] | dict[str, Any]:
        context = self.get_context()
        tool = self._tool_manager.get_tool(name)
        if tool is None:
            raise ToolError(f"Unknown tool: {name}")

        effective_arguments = dict(arguments)
        workspace_token = set_pending_workspace_root(
            resolve_workspace_override(effective_arguments.pop("workspace_root", None))
        )
        progress_token = bind_context(context)
        try:
            result = await tool.fn_metadata.call_fn_with_arg_validation(
                tool.fn,
                tool.is_async,
                effective_arguments,
                {tool.context_kwarg: context} if tool.context_kwarg is not None else None,
            )
            return cast(
                "list[ContentBlock] | dict[str, Any]",
                tool.fn_metadata.convert_result(result),
            )
        except UrlElicitationRequiredError:
            raise
        except McpError:
            raise
        except QSpiceError as exc:
            raise McpError(_to_mcp_error_data(exc)) from exc
        except Exception as exc:
            trace_id = get_exception_trace_id(exc)
            if trace_id is None:
                raise ToolError(f"Error executing tool {name}: {exc}") from exc
            raise ToolError(f"Error executing tool {name} [trace_id={trace_id}]: {exc}") from exc
        finally:
            reset_context(progress_token)
            reset_pending_workspace_root(workspace_token)


def _build_app(
    definition: ServerDefinition,
    settings: QSpiceSettings,
    resources: tuple[ResourceDefinition, ...],
    registered_tools: tuple[ToolDefinition, ...],
    runtime: QSpiceToolRuntime,
) -> FastMCP:
    """Create a FastMCP application and bind implemented tool handlers."""

    app = _QSpiceFastMCP(
        definition.title,
        instructions=definition.instructions,
        log_level=_resolve_mcp_log_level(settings.log_level),
        tool_runtime=runtime,
    )
    for tool in registered_tools:
        app.tool(
            name=tool.name,
            title=tool.title,
            description=tool.description,
            annotations=_to_mcp_annotations(tool.annotations),
            structured_output=True,
        )(runtime.get_handler(tool.name))
    _register_resources(app, resources)
    register_prompts(app, get_prompt_definitions())
    return app


@dataclass(frozen=True, slots=True)
class QSpiceMCPServer:
    """Bootstrapped server metadata and runtime registrations."""

    definition: ServerDefinition
    settings: QSpiceSettings
    tools: tuple[ToolDefinition, ...]
    registered_tools: tuple[ToolDefinition, ...]
    resources: tuple[ResourceDefinition, ...]
    probe: ProbeResult
    adapters: tuple[AdapterDescription, ...]
    selected_adapter: AdapterDescription | None
    tool_runtime: QSpiceToolRuntime
    app: FastMCP

    def summary(self) -> dict[str, object]:
        """Return a JSON-serializable summary of the bootstrap state."""

        return {
            "name": self.definition.name,
            "title": self.definition.title,
            "features": self.definition.features.model_dump(),
            "parameters": [parameter.name for parameter in self.definition.parameters],
            "settings": {
                "transport": self.settings.transport,
                "workspace_root": str(self.settings.workspace_root),
                "cache_dir": str(self.settings.cache_dir),
                "log_level": self.settings.log_level,
                "timeout_s": self.settings.timeout_s,
                "max_cache_bytes": self.settings.max_cache_bytes,
                "telemetry_enabled": self.settings.telemetry_enabled,
            },
            "probe": {
                "configured": self.probe.configured,
                "executable": str(self.probe.executable)
                if self.probe.executable is not None
                else None,
                "exists": self.probe.exists,
                "source": self.probe.source,
                "version": self.probe.version,
                "version_source": self.probe.version_source,
            },
            "selected_adapter": self.selected_adapter.summary()
            if self.selected_adapter is not None
            else None,
            "adapters": [adapter.summary() for adapter in self.adapters],
            "tools": [tool.summary() for tool in self.tools],
            "registered_tools": [tool.name for tool in self.registered_tools],
            "resources": [resource.uri for resource in self.resources],
        }

    def invoke_tool(self, name: str, /, **kwargs: object) -> dict[str, object]:
        """Invoke one bound tool handler directly for tests and local flows."""

        return self.tool_runtime.invoke(name, **kwargs)


def _validate_runtime_handlers(
    runtime: QSpiceToolRuntime,
    registered_tools: tuple[ToolDefinition, ...],
) -> None:
    """Fail fast when an implemented tool lacks a bound runtime handler."""

    missing = [tool.name for tool in registered_tools if tool.name not in runtime._handlers]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RuntimeError(f"Missing MCP runtime handlers for implemented tools: {missing_text}")


def create_server(settings: QSpiceSettings | None = None) -> QSpiceMCPServer:
    """Create the FastMCP-backed server object from current settings."""

    effective_settings = settings.normalized() if settings is not None else build_settings()
    probe = probe_qspice(effective_settings)
    adapters = describe_adapters(probe)
    definition = build_server_definition()
    _logger = get_logger(component="mcp.server")
    try:
        tools = build_tool_registry_from_runtime()
        if not tools:
            tools = build_tool_registry()
    except Exception as exc:
        _logger.warning("build_tool_registry_from_runtime_failed", error=str(exc))
        tools = build_tool_registry()
    registered_tools = build_runtime_tool_registry(tools)
    resources = get_resource_definitions()
    runtime = QSpiceToolRuntime(effective_settings, registered_tools)
    _validate_runtime_handlers(runtime, registered_tools)
    try:
        selected_adapter = select_adapter(probe).describe(probe)
    except AdapterNotFoundError:
        selected_adapter = None
    return QSpiceMCPServer(
        definition=definition,
        settings=effective_settings,
        tools=tools,
        registered_tools=registered_tools,
        resources=resources,
        probe=probe,
        adapters=adapters,
        selected_adapter=selected_adapter,
        tool_runtime=runtime,
        app=_build_app(definition, effective_settings, resources, registered_tools, runtime),
    )


def run(*, settings: QSpiceSettings | None = None, describe: bool = False) -> int:
    """Run the MCP server or print a bootstrap summary."""

    server = create_server(settings)
    logger = get_logger(component="mcp.server", transport=server.settings.transport)
    logger.info(
        "server_bootstrap_ready",
        tool_count=len(server.tools),
        registered_tool_count=len(server.registered_tools),
        resource_count=len(server.resources),
        qspice_available=server.probe.exists,
    )

    if describe:
        print(json.dumps(server.summary(), indent=2))
        return 0

    install_shutdown_hooks()
    server.app.run(transport=server.settings.transport)
    return 0
