"""Tests for declarative MCP handler kwarg normalization."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry
from qspice_mcp.mcp.tools import handler_bindings
from qspice_mcp.mcp.tools.handler_bindings import (
    _attempt_live_gui_reuse,
    _build_service_call_kwargs,
    _normalize_tool_kwargs,
)
from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime
from qspice_mcp.services._internals import live_gui_manager as live_gui_manager_service
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic
from qspice_mcp.services.waveform.read_waveform import read_waveform

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_RUN_NETLIST_BRIDGE = """\
from __future__ import annotations
import datetime, json, pathlib, sys, time
manifest_path = pathlib.Path(sys.argv[1])
payload = json.loads(manifest_path.read_text(encoding='utf-8'))
protocol = payload.get('bridge_protocol', {})
commands_path = pathlib.Path(
    protocol.get('command_queue', {}).get('path')
    or (manifest_path.parent / 'bridge.commands.jsonl')
)
events_path = pathlib.Path(
    protocol.get('event_log', {}).get('path')
    or (manifest_path.parent / 'bridge.events.jsonl')
)
(manifest_path.parent / 'bridge.ready').write_text('ready', encoding='utf-8')
processed = 0
sequence = 0
while True:
    if commands_path.is_file():
        lines = [
            line for line in commands_path.read_text(encoding='utf-8').splitlines() if line.strip()
        ]
        for raw in lines[processed:]:
            command = json.loads(raw)
            command_payload = command.get('payload', {})
            sequence += 1
            event_name = 'command_ack'
            if command.get('command') == 'run_netlist':
                event_name = 'run_netlist_complete'
                for key in ('log_path', 'raw_path'):
                    target = command_payload.get(key)
                    if target:
                        target_path = pathlib.Path(target)
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        target_path.write_text('ok', encoding='utf-8')
            event = {
                'sequence': sequence,
                'event': event_name,
                'command_id': command.get('command_id'),
                'command': command.get('command'),
                'payload': command_payload,
                'created_at': datetime.datetime.now().astimezone().isoformat(),
            }
            with events_path.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps(event) + '\\n')
        processed = len(lines)
    time.sleep(0.05)
"""


def _runtime(tmp_path: Path) -> QSpiceToolRuntime:
    settings = QSpiceSettings(workspace_root=tmp_path)
    return QSpiceToolRuntime(settings, build_runtime_tool_registry())


def _wait_for_file(path: Path, *, deadline_s: float = 5.0) -> None:
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for {path.name}.")


def test_run_simulation_reuses_live_gui_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(live_gui_manager_service.sys, "platform", "win32")

    bridge_script = tmp_path / "bridge.py"
    bridge_script.write_text(_RUN_NETLIST_BRIDGE, encoding="utf-8")
    settings = QSpiceSettings(
        workspace_root=tmp_path,
        session_mode="auto",
        live_gui_bridge_command=(sys.executable, str(bridge_script)),
    )
    runtime = QSpiceToolRuntime(settings, build_runtime_tool_registry())

    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    launched = runtime._live_gui_manager.launch_live_gui_session(
        session_name="reuse", schematic_path=str(schematic)
    )
    netlist = tmp_path / "demo.net"
    netlist.write_text("* netlist\n", encoding="utf-8")

    try:
        _wait_for_file(launched.output_root / "bridge.ready")
        payload = runtime.invoke("run_simulation", source_path="demo.net")
    finally:
        runtime._live_gui_manager.close_live_gui_session(launched.session_id, delete_manifest=True)

    assert payload["session_strategy"] == "reuse_live_gui"
    assert payload["live_gui_session_id"] == launched.session_id
    assert payload["adapter_key"] == "live_gui_bridge"
    assert payload["log_exists"] is True


def test_attempt_live_gui_reuse_returns_none_without_session(tmp_path: Path) -> None:
    settings = QSpiceSettings(workspace_root=tmp_path, session_mode="auto")
    runtime = QSpiceToolRuntime(settings, build_runtime_tool_registry())
    netlist = tmp_path / "demo.net"
    netlist.write_text("* netlist\n", encoding="utf-8")

    result = handler_bindings._attempt_live_gui_reuse(
        runtime,
        netlist_path=netlist,
        original_source=netlist,
        log_path=None,
        raw_output_path=None,
        extra_switches=(),
        timeout_s=None,
    )
    assert result is None
    assert _attempt_live_gui_reuse is handler_bindings._attempt_live_gui_reuse


def test_build_service_call_kwargs_ignores_null_optional_defaults(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        add_component,
        {
            "schematic_path": "demo.qsch",
            "component_kind": "resistor",
            "reference": "R1",
            "value": "1k",
            "rotation_degrees": None,
            "auto_place": None,
        },
    )
    assert "rotation_degrees" not in kwargs
    assert "auto_place" not in kwargs


def test_build_service_call_kwargs_maps_schematic_path_to_raw_path(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        inspect_schematic,
        {"schematic_path": "demo.qsch"},
    )
    assert kwargs["raw_path"] == "demo.qsch"


def test_build_service_call_kwargs_preserves_explicit_none_defaults(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        read_waveform,
        {
            "raw_path": "demo.qraw",
            "signal": "V(out)",
            "component": None,
            "step": None,
        },
    )
    assert "component" not in kwargs
    assert "step" not in kwargs


def test_read_log_handler_accepts_contract_log_path_argument(tmp_path: Path) -> None:
    """The MCP contract exposes log_path; the handler must reach the service with it."""
    runtime = _runtime(tmp_path)
    log_file = tmp_path / "demo.log"
    log_file.write_text("QSPICE analysis log\nTotal elapsed time: 1s\n", encoding="utf-8")

    payload = runtime.get_handler("read_log")(log_path="demo.log", include_measures=False)

    assert payload["line_count"] == 2
    assert str(payload["log_path"]).endswith("demo.log")


def test_normalize_tool_kwargs_coerces_text_roles_to_tuple() -> None:
    normalized = _normalize_tool_kwargs(
        "normalize_component_text_rotation",
        {
            "schematic_path": "demo.qsch",
            "reference": "R1",
            "text_roles": ["refdes", "value"],
        },
    )
    assert normalized["text_roles"] == ("refdes", "value")
