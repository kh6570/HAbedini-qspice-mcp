"""Request trace and optional OpenTelemetry helpers."""

from __future__ import annotations

import importlib
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Protocol, cast
from uuid import uuid4

from structlog.contextvars import bind_contextvars, reset_contextvars

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    class _SpanContextManager(Protocol):
        def __enter__(self) -> object: ...

        def __exit__(self, exc_type: object, exc: object, tb: object) -> bool | None: ...

    class _TracerProtocol(Protocol):
        def start_as_current_span(
            self,
            name: str,
            *,
            attributes: Mapping[str, str | bool | int | float] | None = None,
        ) -> _SpanContextManager: ...

    class _TraceApiProtocol(Protocol):
        def get_tracer(self, name: str) -> _TracerProtocol: ...

        def get_tracer_provider(self) -> object: ...

else:
    _TraceApiProtocol = object
    _TracerProtocol = object

_otel_trace: _TraceApiProtocol | None
try:
    _otel_trace = cast("_TraceApiProtocol", importlib.import_module("opentelemetry.trace"))
except ImportError:  # pragma: no cover - optional dependency
    _otel_trace = None

_TRACER_NAME = "qspice_mcp"
_TRACE_ID_ATTRIBUTE = "_qspice_trace_id"
_DEFAULT_TRACER_PROVIDER_CLASSES = frozenset({"NoOpTracerProvider", "ProxyTracerProvider"})
_CURRENT_TRACE_ID: ContextVar[str | None] = ContextVar("qspice_request_trace_id", default=None)
_CURRENT_TOOL_NAME: ContextVar[str | None] = ContextVar("qspice_request_tool_name", default=None)


def get_current_trace_id() -> str | None:
    """Return the current request-scoped trace identifier when one is active."""

    return _CURRENT_TRACE_ID.get()


def get_current_tool_name() -> str | None:
    """Return the current request-scoped tool name when one is active."""

    return _CURRENT_TOOL_NAME.get()


def attach_trace_id(exc: BaseException, trace_id: str) -> None:
    """Attach one trace identifier to an exception for later error shaping."""

    if getattr(exc, _TRACE_ID_ATTRIBUTE, None) is None:
        setattr(exc, _TRACE_ID_ATTRIBUTE, trace_id)


def get_exception_trace_id(exc: BaseException) -> str | None:
    """Return a previously attached trace identifier from an exception."""

    value = getattr(exc, _TRACE_ID_ATTRIBUTE, None)
    return value if isinstance(value, str) else None


def _get_tracer() -> _TracerProtocol | None:
    if _otel_trace is None:
        return None
    return _otel_trace.get_tracer(_TRACER_NAME)


def _flatten_span_processors(active_processor: object | None) -> tuple[object, ...]:
    if active_processor is None:
        return ()
    nested_processors = getattr(active_processor, "_span_processors", None)
    if isinstance(nested_processors, list | tuple):
        return tuple(processor for processor in nested_processors if processor is not None)
    return (active_processor,)


def _extract_exporter_name(span_processor: object) -> str | None:
    for attribute_name in ("span_exporter", "_span_exporter", "exporter", "_exporter"):
        exporter = getattr(span_processor, attribute_name, None)
        if exporter is not None:
            return type(exporter).__name__
    return None


def describe_telemetry_state(*, telemetry_enabled: bool) -> dict[str, object]:
    """Describe the active runtime telemetry readiness and detected pipeline."""

    dependencies_installed = _otel_trace is not None
    tracer_provider = None if _otel_trace is None else _otel_trace.get_tracer_provider()
    tracer_provider_class = None if tracer_provider is None else type(tracer_provider).__name__
    tracer_provider_configured = (
        tracer_provider_class is not None
        and tracer_provider_class not in _DEFAULT_TRACER_PROVIDER_CLASSES
    )
    active_processor = (
        None
        if tracer_provider is None
        else getattr(tracer_provider, "_active_span_processor", None)
    )
    span_processors = _flatten_span_processors(active_processor)
    span_processor_names = [type(span_processor).__name__ for span_processor in span_processors]
    exporter_names: list[str] = []
    for span_processor in span_processors:
        exporter_name = _extract_exporter_name(span_processor)
        if exporter_name is not None and exporter_name not in exporter_names:
            exporter_names.append(exporter_name)
    exporters_configured = bool(exporter_names)
    spans_emitting = (
        telemetry_enabled
        and dependencies_installed
        and tracer_provider_configured
        and exporters_configured
    )

    notes: list[str] = []
    if not telemetry_enabled:
        notes.append(
            "Telemetry is disabled; set QSPICE_TELEMETRY_ENABLED=true to request "
            "long-running MCP spans."
        )
    if not dependencies_installed:
        notes.append(
            "Optional OpenTelemetry dependencies are not installed; install the telemetry "
            "extra before enabling spans."
        )
    elif not tracer_provider_configured:
        notes.append(
            "No in-process tracer provider is configured, so spans remain no-op even when "
            "telemetry is enabled."
        )
    elif not exporters_configured:
        notes.append(
            "A tracer provider is configured, but no exporter-backed span processor was "
            "detected on it."
        )
    else:
        notes.append(
            "Telemetry is configured; long-running MCP tool spans should be emitted through "
            "the detected exporter pipeline."
        )

    return {
        "enabled": telemetry_enabled,
        "dependencies_installed": dependencies_installed,
        "tracer_provider_configured": tracer_provider_configured,
        "tracer_provider_class": tracer_provider_class,
        "span_processors": span_processor_names,
        "exporters": exporter_names,
        "exporters_configured": exporters_configured,
        "spans_emitting": spans_emitting,
        "notes": notes,
    }


@contextmanager
def operation_span(
    name: str,
    *,
    enabled: bool,
    attributes: Mapping[str, str | bool | int | float] | None = None,
) -> Iterator[None]:
    """Start one optional OpenTelemetry span when telemetry is enabled."""

    tracer = _get_tracer()
    if not enabled or tracer is None:
        yield
        return

    span_attributes = dict(attributes or {})
    trace_id = get_current_trace_id()
    tool_name = get_current_tool_name()
    if trace_id is not None:
        span_attributes.setdefault("qspice.trace_id", trace_id)
    if tool_name is not None:
        span_attributes.setdefault("qspice.tool_name", tool_name)

    with tracer.start_as_current_span(name, attributes=span_attributes):
        yield


@contextmanager
def request_scope(
    *,
    tool_name: str,
    telemetry_enabled: bool,
    long_running: bool,
) -> Iterator[str]:
    """Bind one request-scoped trace identifier and optional root span."""

    trace_id = uuid4().hex
    trace_token = _CURRENT_TRACE_ID.set(trace_id)
    tool_token = _CURRENT_TOOL_NAME.set(tool_name)
    log_tokens = bind_contextvars(trace_id=trace_id, tool_name=tool_name)
    try:
        with operation_span(
            f"mcp.tool.{tool_name}",
            enabled=telemetry_enabled and long_running,
            attributes={
                "qspice.long_running": long_running,
                "qspice.request_scope": True,
            },
        ):
            yield trace_id
    finally:
        reset_contextvars(**log_tokens)
        _CURRENT_TOOL_NAME.reset(tool_token)
        _CURRENT_TRACE_ID.reset(trace_token)


__all__ = [
    "attach_trace_id",
    "describe_telemetry_state",
    "get_current_tool_name",
    "get_current_trace_id",
    "get_exception_trace_id",
    "operation_span",
    "request_scope",
]
