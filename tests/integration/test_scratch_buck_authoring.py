"""Track A end-to-end: author the buck from scratch via MCP tools, then simulate.

Unlike ``test_buck_converter.py`` (which copies the shipped recipe schematic),
this test builds ``Buck-converter.qsch`` from an empty workspace using only the
MCP authoring tools, driven by the shared blueprint
``data/recipes/buck_converter_cpp/scratch_buck.blueprint.json``. It then builds
the controller DLL, generates the netlist, simulates, and asserts ``V(out) > 4V``.
"""

from __future__ import annotations

import json
from importlib.resources import files
from typing import TYPE_CHECKING, Any

import pytest

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services.mixed_signal.build_dll_device import build_dll_device
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.list_signals import list_signals
from qspice_mcp.services.waveform.read_waveform import read_waveform

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration

_RECIPE_PACKAGE = "qspice_mcp.data.recipes.buck_converter_cpp"
_SCHEMATIC_NAME = "Buck-converter.qsch"


def _require_local_qspice_runtime(workspace_root: Path) -> Path:
    probe = probe_qspice(QSpiceSettings(workspace_root=workspace_root))
    if probe.executable is None or not probe.exists:
        pytest.skip("QSpice executable is not available for integration tests.")
    return probe.executable


def _load_blueprint() -> dict[str, Any]:
    raw = (files(_RECIPE_PACKAGE) / "scratch_buck.blueprint.json").read_text(encoding="utf-8")
    blueprint: dict[str, Any] = json.loads(raw)
    return blueprint


def author_scratch_buck(server: Any, blueprint: dict[str, Any]) -> str:
    """Author the full buck schematic via MCP authoring tools; return its name."""

    schematic = str(blueprint["schematic"])
    server.invoke_tool("create_schematic", output_path=schematic, overwrite=True)

    for block in blueprint["dll_blocks"]:
        server.invoke_tool(
            "add_dll_block",
            schematic_path=schematic,
            reference=block["reference"],
            device_name=block["device_name"],
            input_pin_names=list(block["input_pin_names"]),
            output_pin_names=list(block["output_pin_names"]),
            position_x=block["position_x"],
            position_y=block["position_y"],
            rotation_degrees=block["rotation_degrees"],
        )

    for component in blueprint["components"]:
        server.invoke_tool(
            "add_component",
            schematic_path=schematic,
            component_kind=component["kind"],
            reference=component["reference"],
            value=component["value"],
            position_x=component["position_x"],
            position_y=component["position_y"],
            rotation_degrees=component["rotation_degrees"],
        )

    for junction in blueprint["junctions"]:
        server.invoke_tool(
            "add_junction",
            schematic_path=schematic,
            position_x=junction["position_x"],
            position_y=junction["position_y"],
        )

    for label in blueprint["net_labels"]:
        server.invoke_tool(
            "add_net_label",
            schematic_path=schematic,
            position_x=label["position_x"],
            position_y=label["position_y"],
            net_name=label["net"],
        )

    for wire in blueprint["wires"]:
        server.invoke_tool(
            "add_wire",
            schematic_path=schematic,
            start_x=wire["start_x"],
            start_y=wire["start_y"],
            end_x=wire["end_x"],
            end_y=wire["end_y"],
            net_name=wire["net"],
        )

    for parameter in blueprint["parameters"]:
        server.invoke_tool(
            "set_parameter",
            schematic_path=schematic,
            name=parameter["name"],
            value=parameter["value"],
        )

    for instruction in blueprint["instructions"]:
        server.invoke_tool(
            "add_instruction",
            schematic_path=schematic,
            instruction=instruction,
        )

    return schematic


def test_scratch_authored_buck_simulates_to_regulated_output(tmp_path: Path) -> None:
    executable = _require_local_qspice_runtime(tmp_path)
    blueprint = _load_blueprint()

    settings = QSpiceSettings(exe=executable, workspace_root=tmp_path)
    server = create_server(settings)

    schematic_name = author_scratch_buck(server, blueprint)
    schematic_path = tmp_path / schematic_name
    assert schematic_path.is_file()

    # Structural checks before simulating.
    inspected = server.invoke_tool("inspect_schematic", schematic_path=schematic_name)
    components = inspected.get("components", [])
    assert len(components) == len(blueprint["components"]) + len(blueprint["dll_blocks"])

    # Build the controller DLL from the shipped C++ source beside the schematic.
    controller_source = tmp_path / blueprint["dll_source"]
    controller_source.write_bytes(
        (files(_RECIPE_PACKAGE) / str(blueprint["dll_source"])).read_bytes()
    )
    try:
        built = build_dll_device(
            controller_source,
            workspace_root=tmp_path,
            qspice_executable=executable,
            timeout_s=180.0,
        )
    except (BackendUnavailableError, ValidationError) as exc:
        pytest.skip(f"buck_controller.dll could not be built on this machine: {exc}")
    assert built.output_path.is_file()

    generated = generate_netlist(
        schematic_path,
        workspace_root=tmp_path,
        output_path=tmp_path / "Buck-converter.net",
    )
    assert generated.netlist_path.is_file()

    result = run_simulation(
        generated.netlist_path,
        workspace_root=tmp_path,
        settings=settings,
        log_path=tmp_path / "scratch-buck.log",
        raw_output_path=tmp_path / "scratch-buck.qraw",
    )
    assert result.exit_code == 0
    assert result.raw_exists is True

    signal_catalog = list_signals(result.raw_path, workspace_root=tmp_path)
    assert any(signal.name == "V(out)" for signal in signal_catalog.signals)

    waveform = read_waveform(
        result.raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        max_points=256,
    )
    assert waveform.y_values[-1] > 4.0
