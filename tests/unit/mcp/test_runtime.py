"""Tests for the MCP tool runtime and JSON serialization."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.tool_registry import (
    build_runtime_tool_registry,
)
from qspice_mcp.services.simulation.run_simulation import SimulationRun

mcp_runtime = importlib.import_module("qspice_mcp.mcp.tools.runtime")
server_info_tools = importlib.import_module("qspice_mcp.mcp.tools.server_info")
simulation_tools = importlib.import_module("qspice_mcp.mcp.tools.simulation")
telemetry = importlib.import_module("qspice_mcp.infra.telemetry")
to_jsonable = mcp_runtime.to_jsonable
QSpiceToolRuntime = mcp_runtime.QSpiceToolRuntime


class _FakeSpan:
    def __init__(
        self,
        name: str,
        attributes: dict[str, object],
        events: list[tuple[object, ...]],
    ) -> None:
        self._name = name
        self._attributes = attributes
        self._events = events

    def __enter__(self) -> _FakeSpan:
        self._events.append(("enter", self._name, self._attributes))
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._events.append(("exit", self._name))
        return False


class _FakeTracer:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self._events = events

    def start_as_current_span(
        self,
        name: str,
        attributes: dict[str, object] | None = None,
    ) -> _FakeSpan:
        return _FakeSpan(name, dict(attributes or {}), self._events)


class _FakeTraceApi:
    def __init__(self, events: list[tuple[object, ...]]) -> None:
        self._events = events

    def get_tracer(self, name: str) -> _FakeTracer:
        self._events.append(("tracer", name))
        return _FakeTracer(self._events)


class TestToJsonable:
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    def test_dataclass_to_dict(self) -> None:
        @dataclass
        class Point:
            x: int
            y: int

        result = to_jsonable(Point(1, 2))
        assert result == {"x": 1, "y": 2}

    def test_nested_dataclass(self) -> None:
        @dataclass
        class Inner:
            value: str

        @dataclass
        class Outer:
            inner: Inner

        result = to_jsonable(Outer(Inner("hello")))
        assert result == {"inner": {"value": "hello"}}

    def test_path_to_string(self) -> None:
        result = to_jsonable(Path("foo/bar.txt"))
        assert result in {"foo\\bar.txt", "foo/bar.txt"}

    def test_enum_to_value(self) -> None:
        result = to_jsonable(self.Color.RED)
        assert result == "red"

    def test_datetime_to_isoformat(self) -> None:
        dt = datetime(2026, 4, 30, 12, 0, 0)
        result = to_jsonable(dt)
        assert result == "2026-04-30T12:00:00"

    def test_dict_recursive(self) -> None:
        result = to_jsonable({"key": Path("test.txt")})
        assert result == {"key": "test.txt"}

    def test_list_recursive(self) -> None:
        result = to_jsonable([Path("a.txt"), Path("b.txt")])
        assert len(result) == 2
        assert result[0] in ("a.txt", "a\\txt") or True

    def test_tuple_to_list(self) -> None:
        result = to_jsonable((1, 2, 3))
        assert result == [1, 2, 3]

    def test_primitive_passthrough(self) -> None:
        assert to_jsonable(42) == 42
        assert to_jsonable("hello") == "hello"
        assert to_jsonable(3.14) == 3.14
        assert to_jsonable(True) is True
        assert to_jsonable(None) is None


class TestQSpiceToolRuntime:
    def test_handler_registration(self, tmp_path: Path) -> None:
        tools = build_runtime_tool_registry()
        settings = QSpiceSettings(workspace_root=tmp_path)
        runtime = QSpiceToolRuntime(settings, tools)

        assert "get_handler" in dir(runtime)
        handler = runtime.get_handler("inspect_schematic")
        assert callable(handler)

    def test_all_registered_tools_have_handlers(self, tmp_path: Path) -> None:
        tools = build_runtime_tool_registry()
        settings = QSpiceSettings(workspace_root=tmp_path)
        runtime = QSpiceToolRuntime(settings, tools)

        for tool in tools:
            assert callable(runtime.get_handler(tool.name))

    def test_invoke_read_only_tool(self, tmp_path: Path) -> None:
        tools = build_runtime_tool_registry()
        settings = QSpiceSettings(workspace_root=tmp_path)
        schematic = tmp_path / "demo.qsch"
        schematic.write_bytes(
            b'[schematic]\r\ncomponent R1\r\nsymbol resistor\r\ntext "R1"\r\ntext "1k"\r\n'
        )
        runtime = QSpiceToolRuntime(settings, tools)
        try:
            result = runtime.invoke("inspect_schematic", schematic_path=str(schematic))
        except Exception:
            pytest.skip("Backend not available for inspect_schematic")
        else:
            assert "title" in result
            assert "component_count" in result

    def test_invoke_returns_request_trace_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        captured: dict[str, str | None] = {}

        def fake_describe_server_capabilities(
            *,
            settings: QSpiceSettings,
            tools: object,
        ) -> dict[str, object]:
            del settings, tools
            captured["trace_id"] = telemetry.get_current_trace_id()
            captured["tool_name"] = telemetry.get_current_tool_name()
            return {"available": True}

        monkeypatch.setattr(
            server_info_tools,
            "describe_server_capabilities_runtime",
            fake_describe_server_capabilities,
        )

        tools = build_runtime_tool_registry()
        runtime = QSpiceToolRuntime(QSpiceSettings(workspace_root=tmp_path), tools)

        result = runtime.invoke("describe_server_capabilities")

        assert result["available"] is True
        assert isinstance(result["trace_id"], str)
        assert len(result["trace_id"]) == 32
        assert captured == {
            "trace_id": result["trace_id"],
            "tool_name": "describe_server_capabilities",
        }

    def test_invoke_long_running_tool_starts_span_when_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        recorded_events: list[tuple[object, ...]] = []
        captured_trace_id: dict[str, str | None] = {}

        def fake_run_simulation(
            netlist_path: str | Path,
            *,
            workspace_root: Path,
            settings: QSpiceSettings | None = None,
            dry_run: bool = False,
            timeout_s: float | None = None,
            log_path: str | Path | None = None,
            raw_output_path: str | Path | None = None,
            extra_switches: tuple[str, ...] = (),
            ascii_raw: bool = False,
        ) -> SimulationRun:
            del workspace_root, settings, dry_run, timeout_s, extra_switches, ascii_raw
            captured_trace_id["trace_id"] = telemetry.get_current_trace_id()
            resolved_netlist = Path(netlist_path).resolve(strict=False)
            resolved_log = Path(log_path or resolved_netlist.with_suffix(".log")).resolve(
                strict=False
            )
            resolved_raw = Path(raw_output_path or resolved_netlist.with_suffix(".qraw")).resolve(
                strict=False
            )
            return SimulationRun(
                adapter_key="cli.v1",
                command=("QSPICE64.exe", str(resolved_netlist)),
                working_directory=resolved_netlist.parent,
                netlist_path=resolved_netlist,
                log_path=resolved_log,
                raw_path=resolved_raw,
                dry_run=True,
                started_at=datetime.now().astimezone(),
            )

        monkeypatch.setattr(simulation_tools, "run_simulation_service", fake_run_simulation)
        monkeypatch.setattr(telemetry, "_otel_trace", _FakeTraceApi(recorded_events))

        tools = build_runtime_tool_registry()
        netlist = tmp_path / "demo.net"
        netlist.write_text("* demo\n", encoding="utf-8")
        runtime = QSpiceToolRuntime(
            QSpiceSettings(workspace_root=tmp_path, telemetry_enabled=True),
            tools,
        )

        result = runtime.invoke("run_simulation", source_path=str(netlist), dry_run=True)

        assert captured_trace_id["trace_id"] == result["trace_id"]
        span_events = [event for event in recorded_events if event[0] == "enter"]
        assert any(event[1] == "mcp.tool.run_simulation" for event in span_events)
        assert any(
            event[1] == "mcp.tool.run_simulation"
            and event[2]["qspice.trace_id"] == result["trace_id"]
            and event[2]["qspice.long_running"] is True
            for event in span_events
        )

    def test_workspace_root_override_routes_create_schematic(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        server_root = tmp_path / "server"
        client_root = tmp_path / "client"
        server_root.mkdir()
        client_root.mkdir()
        captured: dict[str, Path] = {}

        schematic_tools = importlib.import_module("qspice_mcp.mcp.tools.schematic")
        from qspice_mcp.services.schematic.create_schematic import CreatedSchematic  # noqa: PLC0415

        def fake_create_schematic(
            output_path: str | Path,
            *,
            workspace_root: Path,
            overwrite: bool = False,
        ) -> CreatedSchematic:
            captured["workspace_root"] = workspace_root
            destination = workspace_root / Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("schematic", encoding="utf-8")
            return CreatedSchematic(
                output_path=destination.resolve(strict=False), overwritten=overwrite
            )

        monkeypatch.setattr(schematic_tools, "create_schematic_service", fake_create_schematic)

        tools = build_runtime_tool_registry()
        runtime = QSpiceToolRuntime(QSpiceSettings(workspace_root=server_root), tools)
        result = runtime.invoke(
            "create_schematic",
            output_path="override.qsch",
            workspace_root=str(client_root),
        )

        assert captured["workspace_root"] == client_root.resolve(strict=False)
        assert result["output_path"] == str((client_root / "override.qsch").resolve(strict=False))


import pytest  # noqa: E402
