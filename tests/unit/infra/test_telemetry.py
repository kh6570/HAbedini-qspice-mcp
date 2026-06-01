"""Tests for telemetry helpers."""

from __future__ import annotations

import importlib

telemetry = importlib.import_module("qspice_mcp.infra.telemetry")


class _FakeExporter:
    pass


class _FakeSpanProcessor:
    def __init__(self) -> None:
        self.span_exporter = _FakeExporter()


class _FakeMultiSpanProcessor:
    def __init__(self, span_processors: tuple[object, ...]) -> None:
        self._span_processors = span_processors


class _FakeTracerProvider:
    def __init__(self, span_processors: tuple[object, ...]) -> None:
        self._active_span_processor = _FakeMultiSpanProcessor(span_processors)


class _FakeTraceApi:
    def __init__(self, tracer_provider: object) -> None:
        self._tracer_provider = tracer_provider

    def get_tracer_provider(self) -> object:
        return self._tracer_provider

    def get_tracer(self, name: str) -> object:
        raise AssertionError(name)


def test_describe_telemetry_state_reports_disabled_without_dependencies(
    monkeypatch,
) -> None:
    monkeypatch.setattr(telemetry, "_otel_trace", None)

    state = telemetry.describe_telemetry_state(telemetry_enabled=False)

    assert state["enabled"] is False
    assert state["dependencies_installed"] is False
    assert state["tracer_provider_configured"] is False
    assert state["exporters_configured"] is False
    assert state["spans_emitting"] is False
    assert state["span_processors"] == []
    assert state["exporters"] == []
    assert any("QSPICE_TELEMETRY_ENABLED=true" in note for note in state["notes"])
    assert any("telemetry extra" in note for note in state["notes"])


def test_describe_telemetry_state_reports_provider_and_exporter(monkeypatch) -> None:
    monkeypatch.setattr(
        telemetry,
        "_otel_trace",
        _FakeTraceApi(_FakeTracerProvider((_FakeSpanProcessor(),))),
    )

    state = telemetry.describe_telemetry_state(telemetry_enabled=True)

    assert state["enabled"] is True
    assert state["dependencies_installed"] is True
    assert state["tracer_provider_configured"] is True
    assert state["tracer_provider_class"] == "_FakeTracerProvider"
    assert state["span_processors"] == ["_FakeSpanProcessor"]
    assert state["exporters"] == ["_FakeExporter"]
    assert state["exporters_configured"] is True
    assert state["spans_emitting"] is True
    assert any("detected exporter pipeline" in note for note in state["notes"])
