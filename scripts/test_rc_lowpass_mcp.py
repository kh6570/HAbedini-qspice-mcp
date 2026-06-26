"""Smoke-build an RC low-pass via the MCP runtime handlers (same code path as MCP tools)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry
from qspice_mcp.mcp.tools.handler_bindings import build_raw_tool_handlers
from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime


def _invoke(
    runtime: QSpiceToolRuntime,
    handlers: dict[str, object],
    name: str,
    **kwargs: object,
) -> dict[str, object]:
    handler = handlers[name]
    assert callable(handler)
    return handler(**kwargs)  # type: ignore[operator, return-value]


def main() -> int:
    workspace = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Desktop" / "qspice-mcp-test"
    )
    workspace.mkdir(parents=True, exist_ok=True)
    settings = QSpiceSettings(workspace_root=workspace)
    runtime = QSpiceToolRuntime(settings, build_runtime_tool_registry())
    handlers = build_raw_tool_handlers(runtime, runtime.tools)

    schematic = "rc_lowpass.qsch"
    _invoke(runtime, handlers, "create_schematic", output_path=schematic, overwrite=True)
    _invoke(
        runtime,
        handlers,
        "add_component",
        schematic_path=schematic,
        component_kind="voltage_source",
        reference="V1",
        value="PULSE(0 5 0 1n 1n 500u 1m)",
        position_x=400,
        position_y=400,
    )
    _invoke(
        runtime,
        handlers,
        "add_component",
        schematic_path=schematic,
        component_kind="resistor",
        reference="R1",
        value="1k",
        position_x=800,
        position_y=400,
    )
    _invoke(
        runtime,
        handlers,
        "add_component",
        schematic_path=schematic,
        component_kind="capacitor",
        reference="C1",
        value="1u",
        position_x=1200,
        position_y=400,
    )
    _invoke(
        runtime,
        handlers,
        "add_component",
        schematic_path=schematic,
        component_kind="ground",
        net_name="GND",
        position_x=400,
        position_y=200,
    )
    _invoke(
        runtime,
        handlers,
        "add_component",
        schematic_path=schematic,
        component_kind="ground",
        net_name="GND",
        position_x=1200,
        position_y=200,
    )
    _invoke(
        runtime,
        handlers,
        "add_wire",
        schematic_path=schematic,
        start_reference="V1",
        start_pin="+",
        end_reference="R1",
        end_pin="1",
        net_name="VIN",
    )
    _invoke(
        runtime,
        handlers,
        "add_wire",
        schematic_path=schematic,
        start_reference="R1",
        start_pin="2",
        end_reference="C1",
        end_pin="+",
        net_name="VOUT",
    )
    _invoke(
        runtime,
        handlers,
        "add_instruction",
        schematic_path=schematic,
        instruction=".tran 0 10m 0 10u",
    )
    inspection = _invoke(runtime, handlers, "inspect_schematic", schematic_path=schematic)
    sim = _invoke(runtime, handlers, "run_simulation", source_path=schematic)
    plot = _invoke(
        runtime,
        handlers,
        "plot_waveforms",
        raw_path="rc_lowpass.qraw",
        signals=["V(vout)"],
        title="RC Low-Pass: Capacitor Voltage",
        output_path="rc_lowpass_vout.png",
    )
    summary = {
        "workspace": str(workspace),
        "schematic": schematic,
        "component_count": inspection.get("component_count"),
        "sim_exit_code": sim.get("exit_code"),
        "plot_path": plot.get("plot_path"),
        "signals": [
            item["name"]
            for item in _invoke(runtime, handlers, "list_signals", raw_path="rc_lowpass.qraw").get(
                "signals", []
            )
            if isinstance(item, dict)
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if sim.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
