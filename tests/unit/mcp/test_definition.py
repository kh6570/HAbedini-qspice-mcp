"""Tests for the MCP bootstrap skeleton."""

from __future__ import annotations

import importlib
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.definition import build_server_definition
from qspice_mcp.mcp.server import create_server
from qspice_mcp.mcp.tool_registry import build_tool_registry
from qspice_mcp.services import get_service_specs
from qspice_mcp.services._backends.schematic_editor import (
    SymbolDrawingMetadata,
    SymbolPinMetadata,
    SymbolTextMetadata,
)
from qspice_mcp.services._internals.simulation_batch import SimulationBatch, SimulationBatchRun
from qspice_mcp.services.artifacts.compare_waveforms import (
    WaveformComparison,
    WaveformComparisonRun,
)
from qspice_mcp.services.artifacts.export_derived_raw import DerivedRawExport
from qspice_mcp.services.artifacts.export_measures_csv import MeasureCsvExport
from qspice_mcp.services.artifacts.merge_waveforms import MergedWaveformExport
from qspice_mcp.services.artifacts.summarize_batch import BatchRunSummary, BatchSummary
from qspice_mcp.services.batch.submit_batch import BatchSubmission
from qspice_mcp.services.live_gui.describe_live_gui_support import LiveGuiSupport
from qspice_mcp.services.live_gui.scaffold_live_gui_session import LiveGuiSessionScaffold
from qspice_mcp.services.mixed_signal.build_dll_device import BuiltDllDevice
from qspice_mcp.services.mixed_signal.scaffold_dll_device_from_symbol import (
    DllDeviceSymbolScaffold,
)
from qspice_mcp.services.mixed_signal.validate_dll_symbol_signature import (
    DllSymbolSignatureValidation,
)
from qspice_mcp.services.remote.close_remote_session import RemoteSessionClosure
from qspice_mcp.services.remote.download_remote_artifacts import RemoteArtifactDownload
from qspice_mcp.services.remote.poll_remote_run import RemoteRunStatus
from qspice_mcp.services.remote.submit_remote_simulation import RemoteSimulationSubmission
from qspice_mcp.services.schematic.add_component import AddedComponent
from qspice_mcp.services.schematic.add_component_symbol_drawing import (
    ComponentSymbolDrawingAdd,
)
from qspice_mcp.services.schematic.add_dll_block import AddedDllBlock
from qspice_mcp.services.schematic.add_dll_block_pin import AddedDllBlockPin
from qspice_mcp.services.schematic.add_instruction import InstructionAdd
from qspice_mcp.services.schematic.add_net_label import AddedNetLabel
from qspice_mcp.services.schematic.add_wire import AddedWire
from qspice_mcp.services.schematic.create_schematic import CreatedSchematic
from qspice_mcp.services.schematic.create_starter_schematic import CreatedStarterSchematic
from qspice_mcp.services.schematic.list_components import ComponentCatalog, ComponentSummary
from qspice_mcp.services.schematic.read_component import ComponentRead
from qspice_mcp.services.schematic.read_component_symbol import ComponentSymbolRead
from qspice_mcp.services.schematic.remove_component_symbol_drawing import (
    ComponentSymbolDrawingRemoval,
)
from qspice_mcp.services.schematic.remove_dll_block_pin import RemovedDllBlockPin
from qspice_mcp.services.schematic.remove_instruction import InstructionRemoval
from qspice_mcp.services.schematic.save_schematic_as import SavedSchematic
from qspice_mcp.services.schematic.set_component_symbol_drawing import (
    ComponentSymbolDrawingUpdate,
)
from qspice_mcp.services.schematic.set_component_symbol_pin import ComponentSymbolPinUpdate
from qspice_mcp.services.schematic.set_component_symbol_text import ComponentSymbolTextUpdate
from qspice_mcp.services.schematic.set_component_value import ComponentValueUpdate
from qspice_mcp.services.schematic.set_dll_block_pin_role import DllBlockPinRoleUpdate
from qspice_mcp.services.simulation.generate_netlist import GeneratedNetlist
from qspice_mcp.services.simulation.run_simulation import SimulationRun
from qspice_mcp.services.simulation.save_netlist_copy import SavedNetlistCopy
from qspice_mcp.services.subcircuit.list_subcircuits import SubcircuitCatalog, SubcircuitSummary
from qspice_mcp.services.subcircuit.read_subcircuit import (
    SubcircuitComponentSummary,
    SubcircuitRead,
)
from qspice_mcp.services.subcircuit.set_subcircuit_component_value import (
    SubcircuitComponentValueUpdate,
)
from qspice_mcp.services.waveform.list_steps import StepCatalog, StepSummary
from qspice_mcp.services.waveform.read_measures import MeasureRead, MeasureResult, MeasureRow

mcp_runtime = importlib.import_module("qspice_mcp.mcp.tools.runtime")
mcp_artifact_tools = importlib.import_module("qspice_mcp.mcp.tools.artifacts")
mcp_live_gui_tools = importlib.import_module("qspice_mcp.mcp.tools.live_gui")
mcp_mixed_signal_tools = importlib.import_module("qspice_mcp.mcp.tools.mixed_signal")
mcp_schematic_tools = importlib.import_module("qspice_mcp.mcp.tools.schematic")
mcp_simulation_tools = importlib.import_module("qspice_mcp.mcp.tools.simulation")
mcp_subcircuit_tools = importlib.import_module("qspice_mcp.mcp.tools.subcircuit")
mcp_waveform_tools = importlib.import_module("qspice_mcp.mcp.tools.waveform")


def test_server_definition_exposes_expected_identity() -> None:
    definition = build_server_definition()

    assert definition.name == "qspice-mcp"
    assert definition.title == "QSpice MCP Server"
    assert definition.parameters[0].name == "qspice-exe"


def test_tool_registry_matches_service_catalog() -> None:
    service_specs = get_service_specs()
    tools = build_tool_registry(service_specs)

    assert len(tools) == len(service_specs)
    assert tuple(tool.name for tool in tools) == tuple(spec.name for spec in service_specs)


def test_create_server_collects_bootstrap_summary(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    summary = server.summary()

    assert summary["settings"]["workspace_root"] == str(tmp_path.resolve())
    assert summary["probe"]["exists"] is True
    assert summary["selected_adapter"]["key"] == "cli.v1"
    assert len(summary["tools"]) == len(build_tool_registry())
    assert "add_instruction" in summary["registered_tools"]
    assert "create_schematic" in summary["registered_tools"]
    assert "create_starter_schematic" in summary["registered_tools"]
    assert "add_component" in summary["registered_tools"]
    assert "add_dll_block" in summary["registered_tools"]
    assert "add_dll_block_pin" in summary["registered_tools"]
    assert "build_dll_device" in summary["registered_tools"]
    assert "add_junction" in summary["registered_tools"]
    assert "describe_topology_authoring_support" in summary["registered_tools"]
    assert "list_workflow_instructions" in summary["registered_tools"]
    assert "read_workflow_instruction" in summary["registered_tools"]
    assert "write_workspace_text_file" in summary["registered_tools"]
    assert "materialize_reference_circuit" in summary["registered_tools"]
    assert "list_reference_circuit_recipes" in summary["registered_tools"]
    assert "describe_reference_circuit_recipe" in summary["registered_tools"]
    assert "scaffold_dll_device_from_symbol" in summary["registered_tools"]
    assert "validate_dll_symbol_signature" in summary["registered_tools"]
    assert "add_wire" in summary["registered_tools"]
    assert "remove_dll_block_pin" in summary["registered_tools"]
    assert "set_dll_block_pin_role" in summary["registered_tools"]
    assert "add_net_label" in summary["registered_tools"]
    assert "list_components" in summary["registered_tools"]
    assert "read_component" in summary["registered_tools"]
    assert "read_component_symbol" in summary["registered_tools"]
    assert "add_component_symbol_drawing" in summary["registered_tools"]
    assert "describe_live_gui_support" in summary["registered_tools"]
    assert "scaffold_live_gui_session" in summary["registered_tools"]
    assert "set_component_symbol_drawing" in summary["registered_tools"]
    assert "set_component_symbol_text" in summary["registered_tools"]
    assert "set_component_symbol_pin" in summary["registered_tools"]
    assert "remove_component_symbol_drawing" in summary["registered_tools"]
    assert "set_component_value" in summary["registered_tools"]
    assert "save_netlist_copy" in summary["registered_tools"]
    assert "run_simulation" in summary["registered_tools"]
    assert "list_steps" in summary["registered_tools"]
    assert "read_measures" in summary["registered_tools"]


def test_create_server_binds_handlers_for_all_implemented_tools(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    for tool in server.registered_tools:
        server.tool_runtime.get_handler(tool.name)


def test_mcp_add_component_accepts_buck_power_stage_kinds(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    created = server.invoke_tool("create_schematic", output_path="buck.qsch", overwrite=True)
    schematic_path = str(created["output_path"])

    for kind, reference, value in (
        ("inductor", "L1", "50µ"),
        ("nmos", "M1", "BSC123N08NS3"),
        ("behavioral", "B1", "V=V(PWM)"),
    ):
        result = server.invoke_tool(
            "add_component",
            schematic_path=schematic_path,
            component_kind=kind,
            reference=reference,
            value=value,
        )
        assert result["component_kind"] == kind


def test_mcp_write_workspace_text_file_auto_builds_cpp_dll(
    monkeypatch: object, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    captured: dict[str, object] = {}

    def fake_build_dll_device(
        source_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path | None = None,
        toolchain: str = "auto",
        timeout_s: float | None = 120.0,
        qspice_executable: Path | None = None,
    ) -> BuiltDllDevice:
        captured["qspice_executable"] = qspice_executable
        _ = workspace_root, output_path, toolchain, timeout_s
        dll_path = tmp_path / "buck_controller.dll"
        dll_path.write_bytes(b"MZ")
        return BuiltDllDevice(
            source_path=tmp_path / "buck_controller.cpp",
            output_path=dll_path,
            toolchain="dmc",
            command=("dmc", "-mn", "-WD"),
            exit_code=0,
            duration_s=0.1,
            stdout="",
            stderr="",
        )

    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setattr(
        "qspice_mcp.mcp.tools.workspace_files.build_dll_device_service",
        fake_build_dll_device,
    )

    result = server.invoke_tool(
        "write_workspace_text_file",
        relative_path="buck_controller.cpp",
        content="extern int x;\n",
        overwrite=True,
        build_dll_after_write=True,
    )

    assert result["output_path"].endswith("buck_controller.cpp")
    assert result["dll_build"]["toolchain"] == "dmc"
    assert Path(result["dll_build"]["output_path"]).name == "buck_controller.dll"
    assert captured["qspice_executable"] == executable


def test_mcp_write_workspace_text_file_reports_dll_build_error(
    monkeypatch: object, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    def fail_build(*_args: object, **_kwargs: object) -> BuiltDllDevice:
        from qspice_mcp.core.exceptions import BackendUnavailableError

        raise BackendUnavailableError("no toolchain")

    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setattr(
        "qspice_mcp.mcp.tools.workspace_files.build_dll_device_service",
        fail_build,
    )

    result = server.invoke_tool(
        "write_workspace_text_file",
        relative_path="buck_controller.cpp",
        content="// test\n",
        overwrite=True,
    )

    assert result["output_path"].endswith("buck_controller.cpp")
    assert "dll_build_error" in result
    assert "no toolchain" in str(result["dll_build_error"])


def test_mcp_write_workspace_text_file_reuses_existing_dll_for_validation(
    monkeypatch: object, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    source = tmp_path / "buck_controller.cpp"
    source.write_text("extern int x;\n", encoding="utf-8")
    dll = tmp_path / "buck_controller.dll"
    dll.write_bytes(b"MZ")

    def fail_build(*_args: object, **_kwargs: object) -> BuiltDllDevice:
        from qspice_mcp.core.exceptions import BackendUnavailableError

        raise BackendUnavailableError("no toolchain")

    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setattr(
        "qspice_mcp.mcp.tools.workspace_files.build_dll_device_service",
        fail_build,
    )

    result = server.invoke_tool(
        "write_workspace_text_file",
        relative_path="buck_controller.cpp",
        content="extern int x;\n",
        overwrite=True,
        build_dll_after_write=True,
    )

    assert result["dll_build"]["skipped_rebuild"] is True
    assert result["dll_build"]["toolchain"] == "existing"
    assert "dll_build_error" not in result


def test_mcp_read_workflow_instruction_returns_buck_scratch_doc(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    result = server.invoke_tool(
        "read_workflow_instruction",
        instruction_id="buck-converter-cpp",
    )

    assert result["instruction_id"] == "buck-converter-cpp"
    assert "add_component" in result["content"]
    assert "nmos" in result["content"]


def test_mcp_run_simulation_accepts_schematic_source(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    generated_net = tmp_path / "demo.net"

    calls: list[tuple[str, object]] = []
    typed_monkeypatch = monkeypatch

    def fake_generate_netlist(
        raw_path: str | Path, *, workspace_root: Path, output_path: str | Path | None = None
    ) -> GeneratedNetlist:
        calls.append(("generate_netlist", Path(raw_path)))
        return GeneratedNetlist(
            source_path=Path(raw_path).resolve(strict=False),
            netlist_path=generated_net.resolve(strict=False),
            source_kind="schematic",
            refreshed=True,
            copied=False,
            warnings=("generated",),
        )

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
        del settings, dry_run, timeout_s, log_path, raw_output_path, extra_switches, ascii_raw
        calls.append(("run_simulation", Path(netlist_path)))
        return SimulationRun(
            adapter_key="cli.v1",
            command=("QSPICE64.exe", str(netlist_path)),
            working_directory=workspace_root.resolve(strict=False),
            netlist_path=Path(netlist_path).resolve(strict=False),
            log_path=(workspace_root / "demo.log").resolve(strict=False),
            raw_path=(workspace_root / "demo.qraw").resolve(strict=False),
            dry_run=False,
            started_at=__import__("datetime").datetime.now().astimezone(),
            exit_code=0,
            duration_s=0.1,
        )

    typed_monkeypatch.setattr(
        mcp_simulation_tools, "generate_netlist_service", fake_generate_netlist
    )
    typed_monkeypatch.setattr(mcp_simulation_tools, "run_simulation_service", fake_run_simulation)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("run_simulation", source_path="demo.qsch")

    assert calls == [
        ("generate_netlist", schematic.resolve(strict=False)),
        ("run_simulation", generated_net.resolve(strict=False)),
    ]
    assert result["source_path"] == str(schematic.resolve(strict=False))
    assert result["generated_netlist"]["netlist_path"] == str(generated_net.resolve(strict=False))


def test_mcp_list_steps_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_list_steps(raw_path: str | Path, *, workspace_root: Path) -> StepCatalog:
        assert workspace_root == tmp_path.resolve(strict=False)
        return StepCatalog(
            raw_path=Path(raw_path).resolve(strict=False),
            log_path=(tmp_path / "demo.log").resolve(strict=False),
            step_count=2,
            step_variables=(),
            steps=(
                StepSummary(index=0, values={"vin": 10}),
                StepSummary(index=1, values={"vin": 12}),
            ),
        )

    typed_monkeypatch.setattr(mcp_waveform_tools, "list_steps_service", fake_list_steps)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("list_steps", raw_path="demo.qraw")

    assert result["step_count"] == 2
    assert result["steps"][1]["values"]["vin"] == 12


def test_mcp_list_components_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_list_components(
        schematic_path: str | Path, *, workspace_root: Path, prefixes: str = "*"
    ) -> ComponentCatalog:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert prefixes == "R"
        return ComponentCatalog(
            schematic_path=Path(schematic_path).resolve(strict=False),
            component_count=1,
            prefixes=prefixes,
            components=(
                ComponentSummary(
                    reference="R1",
                    kind="R",
                    value="1k",
                    description="Resistor",
                    node_count=2,
                    has_subcircuit=False,
                ),
            ),
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "list_components_service", fake_list_components)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("list_components", schematic_path="demo.qsch", prefixes="R")

    assert result["component_count"] == 1
    assert result["components"][0]["reference"] == "R1"


def test_mcp_create_schematic_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_create_schematic(
        output_path: str | Path,
        *,
        workspace_root: Path,
        overwrite: bool = False,
    ) -> CreatedSchematic:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert overwrite is False
        return CreatedSchematic(
            output_path=(tmp_path / Path(output_path)).resolve(strict=False),
            overwritten=False,
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "create_schematic_service",
        fake_create_schematic,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("create_schematic", output_path="blank.qsch")

    assert result["output_path"] == str((tmp_path / "blank.qsch").resolve(strict=False))
    assert result["overwritten"] is False


def test_mcp_add_component_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_component(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        component_kind: str,
        reference: str | None = None,
        value: str | int | float | complex | None = None,
        position_x: int = 0,
        position_y: int = 0,
        rotation_degrees: int = 0,
        net_name: str | None = None,
        output_path: str | Path | None = None,
    ) -> AddedComponent:
        del net_name, output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert component_kind == "resistor"
        assert reference == "R1"
        assert value == "10k"
        assert (position_x, position_y, rotation_degrees) == (160, 240, 90)
        return AddedComponent(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            component_kind=component_kind,
            reference=reference,
            value=str(value),
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            net_name=None,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_component_service", fake_add_component)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_component",
        schematic_path="demo.qsch",
        component_kind="resistor",
        reference="R1",
        value="10k",
        position_x=160,
        position_y=240,
        rotation_degrees=90,
    )

    assert result["reference"] == "R1"
    assert result["component_kind"] == "resistor"
    assert result["position_x"] == 160
    assert result["rotation_degrees"] == 90


def test_mcp_add_component_supports_ground(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_component(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        component_kind: str,
        reference: str | None = None,
        value: str | int | float | complex | None = None,
        position_x: int = 0,
        position_y: int = 0,
        rotation_degrees: int = 0,
        net_name: str | None = None,
        output_path: str | Path | None = None,
    ) -> AddedComponent:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert component_kind == "ground"
        assert reference is None
        assert value is None
        assert net_name is None
        assert (position_x, position_y, rotation_degrees) == (0, 400, 0)
        return AddedComponent(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=Path(schematic_path).resolve(strict=False),
            component_kind=component_kind,
            reference=reference,
            value=None,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            net_name="GND",
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_component_service", fake_add_component)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_component",
        schematic_path="demo.qsch",
        component_kind="ground",
        position_x=0,
        position_y=400,
    )

    assert result["component_kind"] == "ground"
    assert result["net_name"] == "GND"
    assert result["reference"] is None


def test_mcp_add_dll_block_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_dll_block(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        device_name: str,
        input_pin_names: tuple[str, ...] | list[str] = ("in0",),
        output_pin_names: tuple[str, ...] | list[str] = ("out0",),
        position_x: int = 0,
        position_y: int = 0,
        rotation_degrees: int = 0,
        output_path: str | Path | None = None,
    ) -> AddedDllBlock:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert device_name == "Buck_controller"
        assert tuple(input_pin_names) == ("in0", "clk")
        assert tuple(output_pin_names) == ("pwm",)
        assert (position_x, position_y, rotation_degrees) == (300, 100, 45)
        return AddedDllBlock(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            device_name=device_name,
            input_pin_names=tuple(input_pin_names),
            output_pin_names=tuple(output_pin_names),
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_dll_block_service", fake_add_dll_block)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_dll_block",
        schematic_path="demo.qsch",
        reference="X1",
        device_name="Buck_controller",
        input_pin_names=["in0", "clk"],
        output_pin_names=["pwm"],
        position_x=300,
        position_y=100,
        rotation_degrees=45,
    )

    assert result["reference"] == "X1"
    assert result["device_name"] == "Buck_controller"
    assert result["input_pin_names"] == ["in0", "clk"]
    assert result["output_pin_names"] == ["pwm"]


def test_mcp_add_dll_block_pin_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_dll_block_pin(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        pin_name: str,
        direction: str,
        insert_index: int | None = None,
        output_path: str | Path | None = None,
    ) -> AddedDllBlockPin:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert pin_name == "clk"
        assert direction == "input"
        assert insert_index == 1
        return AddedDllBlockPin(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            pin=SymbolPinMetadata(1, pin_name, -800, -200, 150, -50, 0, 14, 145, "0x0", -1),
            input_pin_names=("in0", "clk"),
            output_pin_names=("out0",),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools, "add_dll_block_pin_service", fake_add_dll_block_pin
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_dll_block_pin",
        schematic_path="demo.qsch",
        reference="X1",
        pin_name="clk",
        direction="input",
        insert_index=1,
    )

    assert result["reference"] == "X1"
    assert result["pin"]["name"] == "clk"
    assert result["input_pin_names"] == ["in0", "clk"]


def test_mcp_validate_dll_symbol_signature_is_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    source = tmp_path / "buck_controller.cpp"
    source.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_validate_dll_symbol_signature(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        source_path: str | Path,
    ) -> DllSymbolSignatureValidation:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert Path(source_path).name == "buck_controller.cpp"
        return DllSymbolSignatureValidation(
            schematic_path=Path(schematic_path).resolve(strict=False),
            source_path=Path(source_path).resolve(strict=False),
            reference=reference,
            device_name="Buck_controller",
            expected_export_name="Buck_controller",
            matched_export_name="buck_controller",
            exported_function_names=("buck_controller",),
            symbol_input_pin_names=("in0", "clk"),
            symbol_output_pin_names=("pwm",),
            source_input_pin_names=("in0", "clk"),
            source_output_pin_names=("pwm",),
            is_valid=True,
            mismatches=(),
            warnings=(),
        )

    typed_monkeypatch.setattr(
        mcp_mixed_signal_tools,
        "validate_dll_symbol_signature_service",
        fake_validate_dll_symbol_signature,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "validate_dll_symbol_signature",
        schematic_path="demo.qsch",
        reference="X1",
        source_path="buck_controller.cpp",
    )

    assert result["reference"] == "X1"
    assert result["matched_export_name"] == "buck_controller"
    assert result["is_valid"] is True


def test_mcp_scaffold_dll_device_from_symbol_is_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_scaffold_dll_device_from_symbol(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        settings: object,
        reference: str,
        output_dir: str | None = None,
    ) -> DllDeviceSymbolScaffold:
        del settings
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert output_dir is None
        return DllDeviceSymbolScaffold(
            schematic_path=Path(schematic_path).resolve(strict=False),
            reference=reference,
            device_name="Buck_controller",
            export_name="Buck_controller",
            input_pin_names=("in0", "clk"),
            output_pin_names=("pwm",),
            source_path=(tmp_path / "Buck_controller" / "Buck_controller.cpp").resolve(
                strict=False
            ),
            cmake_path=(tmp_path / "Buck_controller" / "CMakeLists.txt").resolve(strict=False),
            source_line_count=24,
            cmake_line_count=12,
            notes=("Derived from X1.",),
        )

    typed_monkeypatch.setattr(
        mcp_mixed_signal_tools,
        "scaffold_dll_device_from_symbol_service",
        fake_scaffold_dll_device_from_symbol,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "scaffold_dll_device_from_symbol",
        schematic_path="demo.qsch",
        reference="X1",
    )

    assert result["reference"] == "X1"
    assert result["device_name"] == "Buck_controller"
    assert result["input_pin_names"] == ["in0", "clk"]


def test_mcp_create_starter_schematic_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_create_starter_schematic(
        output_path: str | Path,
        *,
        workspace_root: Path,
        overwrite: bool = False,
        source_reference: str = "V1",
        source_value: str | int | float = "10",
        load_reference: str = "R1",
        load_value: str | int | float = "1k",
        output_net_name: str = "VOUT",
        analysis_instruction: str = ".op",
    ) -> CreatedStarterSchematic:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert overwrite is False
        assert source_reference == "V1"
        assert str(source_value) == "10"
        assert load_reference == "R1"
        assert str(load_value) == "1k"
        assert output_net_name == "VOUT"
        assert analysis_instruction == ".op"
        return CreatedStarterSchematic(
            output_path=(tmp_path / Path(output_path)).resolve(strict=False),
            overwritten=False,
            source_reference=source_reference,
            source_value=str(source_value),
            load_reference=load_reference,
            load_value=str(load_value),
            output_net_name=output_net_name,
            analysis_instruction=analysis_instruction,
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "create_starter_schematic_service",
        fake_create_starter_schematic,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("create_starter_schematic", output_path="starter.qsch")

    assert result["output_path"] == str((tmp_path / "starter.qsch").resolve(strict=False))
    assert result["source_reference"] == "V1"
    assert result["load_reference"] == "R1"


def test_mcp_add_wire_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_wire(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        start_x: int | None = None,
        start_y: int | None = None,
        end_x: int | None = None,
        end_y: int | None = None,
        start_reference: str | None = None,
        start_pin: str | None = None,
        end_reference: str | None = None,
        end_pin: str | None = None,
        net_name: str,
        output_path: str | Path | None = None,
    ) -> AddedWire:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert (start_x, start_y, end_x, end_y) == (0, 0, 400, 0)
        assert start_reference is None
        assert start_pin is None
        assert end_reference is None
        assert end_pin is None
        assert net_name == "VIN"
        return AddedWire(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            net_name=net_name,
            start_reference=start_reference,
            start_pin=start_pin,
            end_reference=end_reference,
            end_pin=end_pin,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_wire_service", fake_add_wire)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_wire",
        schematic_path="demo.qsch",
        start_x=0,
        start_y=0,
        end_x=400,
        end_y=0,
        net_name="VIN",
    )

    assert result["net_name"] == "VIN"
    assert result["end_x"] == 400


def test_mcp_add_wire_supports_pin_selected_endpoints(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_wire(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        start_x: int | None = None,
        start_y: int | None = None,
        end_x: int | None = None,
        end_y: int | None = None,
        start_reference: str | None = None,
        start_pin: str | None = None,
        end_reference: str | None = None,
        end_pin: str | None = None,
        net_name: str,
        output_path: str | Path | None = None,
    ) -> AddedWire:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert start_reference == "V1"
        assert start_pin == "+"
        assert end_reference == "R1"
        assert end_pin == "1"
        assert net_name == "VOUT"
        return AddedWire(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            start_x=400,
            start_y=600,
            end_x=800,
            end_y=600,
            net_name=net_name,
            start_reference=start_reference,
            start_pin=start_pin,
            end_reference=end_reference,
            end_pin=end_pin,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_wire_service", fake_add_wire)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_wire",
        schematic_path="demo.qsch",
        start_reference="V1",
        start_pin="+",
        end_reference="R1",
        end_pin="1",
        net_name="VOUT",
    )

    assert result["start_reference"] == "V1"
    assert result["start_pin"] == "+"
    assert result["end_x"] == 800


def test_mcp_add_net_label_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_net_label(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        position_x: int,
        position_y: int,
        net_name: str,
        output_path: str | Path | None = None,
    ) -> AddedNetLabel:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert (position_x, position_y) == (0, 0)
        assert net_name == "VIN"
        return AddedNetLabel(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            position_x=position_x,
            position_y=position_y,
            net_name=net_name,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_net_label_service", fake_add_net_label)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_net_label",
        schematic_path="demo.qsch",
        position_x=0,
        position_y=0,
        net_name="VIN",
    )

    assert result["net_name"] == "VIN"
    assert result["position_y"] == 0


def test_mcp_list_subcircuits_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_list_subcircuits(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instance_path: list[str] | None = None,
    ) -> SubcircuitCatalog:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert instance_path == ["X1"]
        return SubcircuitCatalog(
            schematic_path=Path(schematic_path).resolve(strict=False),
            instance_path=("X1",),
            subcircuit_count=1,
            subcircuits=(
                SubcircuitSummary(
                    reference="X1",
                    definition_name="COMPARATOR",
                    description="Comparator",
                    definition_available=True,
                    component_count=2,
                ),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_subcircuit_tools, "list_subcircuits_service", fake_list_subcircuits
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "list_subcircuits", schematic_path="demo.qsch", instance_path=["X1"]
    )

    assert result["instance_path"] == ["X1"]
    assert result["subcircuit_count"] == 1
    assert result["subcircuits"][0]["reference"] == "X1"


def test_mcp_read_subcircuit_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_read_subcircuit(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        scope: str = "instance",
        instance_path: list[str] | None = None,
    ) -> SubcircuitRead:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert scope == "definition"
        assert instance_path == ["ROOT"]
        return SubcircuitRead(
            schematic_path=Path(schematic_path).resolve(strict=False),
            instance_path=("ROOT",),
            reference=reference,
            scope="definition",
            definition_name="COMPARATOR",
            description="Comparator",
            component_count=1,
            components=(
                SubcircuitComponentSummary(
                    reference="R1",
                    kind="R",
                    value="2k",
                    description="Feedback",
                    node_count=2,
                ),
            ),
            warnings=("definition",),
        )

    typed_monkeypatch.setattr(mcp_subcircuit_tools, "read_subcircuit_service", fake_read_subcircuit)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "read_subcircuit",
        schematic_path="demo.qsch",
        reference="X1",
        scope="definition",
        instance_path=["ROOT"],
    )

    assert result["instance_path"] == ["ROOT"]
    assert result["definition_name"] == "COMPARATOR"
    assert result["components"][0]["reference"] == "R1"


def test_mcp_save_netlist_copy_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    source = tmp_path / "demo.qsch"
    source.write_text("schematic", encoding="utf-8")
    output = tmp_path / "artifacts" / "demo-copy.net"
    typed_monkeypatch = monkeypatch

    def fake_save_netlist_copy(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path,
    ) -> SavedNetlistCopy:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qsch"
        assert output_path == "artifacts/demo-copy.net"
        return SavedNetlistCopy(
            source_path=source.resolve(strict=False),
            output_path=output.resolve(strict=False),
            source_kind="schematic",
            refreshed=True,
            copied=True,
            warnings=("saved",),
        )

    typed_monkeypatch.setattr(
        mcp_simulation_tools, "save_netlist_copy_service", fake_save_netlist_copy
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "save_netlist_copy",
        source_path="demo.qsch",
        output_path="artifacts/demo-copy.net",
    )

    assert result["output_path"] == str(output.resolve(strict=False))
    assert result["copied"] is True


def test_mcp_set_subcircuit_component_value_accepts_instance_path(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    output = tmp_path / "edited.qsch"
    typed_monkeypatch = monkeypatch

    def fake_set_subcircuit_component_value(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        component_reference: str,
        value: str | int | float,
        scope: str = "instance",
        instance_path: list[str] | None = None,
        output_path: str | None = None,
    ) -> SubcircuitComponentValueUpdate:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert schematic_path == "demo.qsch"
        assert reference == "X2"
        assert component_reference == "R1"
        assert value == "5k"
        assert scope == "instance"
        assert instance_path == ["X1"]
        assert output_path == "edited.qsch"
        return SubcircuitComponentValueUpdate(
            schematic_path=schematic.resolve(strict=False),
            output_path=output.resolve(strict=False),
            instance_path=("X1",),
            reference=reference,
            component_reference=component_reference,
            scope="instance",
            value="5k",
        )

    typed_monkeypatch.setattr(
        mcp_subcircuit_tools,
        "set_subcircuit_component_value_service",
        fake_set_subcircuit_component_value,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_subcircuit_component_value",
        schematic_path="demo.qsch",
        reference="X2",
        component_reference="R1",
        value="5k",
        instance_path=["X1"],
        output_path="edited.qsch",
    )

    assert result["instance_path"] == ["X1"]
    assert result["value"] == "5k"


def test_mcp_summarize_batch_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    manifest = tmp_path / "batch.json"
    manifest.write_text("{}", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_summarize_batch(batch_path: str | Path, *, workspace_root: Path) -> BatchSummary:
        assert workspace_root == tmp_path.resolve(strict=False)
        return BatchSummary(
            manifest_path=Path(batch_path).resolve(strict=False),
            batch_id="batch-a",
            source_path=(tmp_path / "demo.qsch").resolve(strict=False),
            output_root=tmp_path.resolve(strict=False),
            sweep_kind="component_value",
            status="completed",
            run_count=1,
            completed_run_count=1,
            successful_run_count=1,
            failed_run_count=0,
            runs=(
                BatchRunSummary(
                    index=0,
                    label="R4=10",
                    assignment={"value": 10},
                    schematic_path=(tmp_path / "demo.qsch").resolve(strict=False),
                    netlist_path=(tmp_path / "demo.net").resolve(strict=False),
                    log_path=(tmp_path / "demo.log").resolve(strict=False),
                    raw_path=(tmp_path / "demo.qraw").resolve(strict=False),
                    exit_code=0,
                    duration_s=0.1,
                    dry_run=False,
                    log_available=True,
                    raw_available=True,
                ),
            ),
        )

    typed_monkeypatch.setattr(mcp_artifact_tools, "summarize_batch_service", fake_summarize_batch)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("summarize_batch", batch_path="batch.json")

    assert result["batch_id"] == "batch-a"
    assert result["runs"][0]["label"] == "R4=10"


def test_mcp_export_measures_csv_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    manifest = tmp_path / "batch.json"
    manifest.write_text("{}", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_export_measures_csv(
        batch_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | None = None,
        measures: list[str] | None = None,
        refresh_measures: bool = True,
    ) -> MeasureCsvExport:
        del measures, refresh_measures
        assert workspace_root == tmp_path.resolve(strict=False)
        return MeasureCsvExport(
            manifest_path=Path(batch_path).resolve(strict=False),
            batch_id="batch-a",
            output_path=(tmp_path / (output_path or "measures.csv")).resolve(strict=False),
            run_count=1,
            exported_run_count=1,
            row_count=2,
            columns=("run_index", "value_value"),
            measure_names=("vout_avg",),
        )

    typed_monkeypatch.setattr(
        mcp_artifact_tools, "export_measures_csv_service", fake_export_measures_csv
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "export_measures_csv", batch_path="batch.json", output_path="out.csv"
    )

    assert result["batch_id"] == "batch-a"
    assert result["output_path"].endswith("out.csv")


def test_mcp_export_derived_raw_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_export_derived_raw(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        signals: list[str],
        output_path: str | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        all_steps: bool = False,
        component: str = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> DerivedRawExport:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert signals == ["V(out)"]
        assert output_path == "derived.qraw"
        assert step == 1
        assert step_filters == {"temp": 25}
        assert all_steps is False
        assert component == "real"
        assert t_start == 0.1
        assert t_end == 0.2
        return DerivedRawExport(
            raw_path=Path(raw_path).resolve(strict=False),
            output_path=(tmp_path / output_path).resolve(strict=False),
            plot_name="Transient Analysis",
            axis_name="time",
            axis_trace_name="time",
            step=1,
            step_count=1,
            point_count=10,
            resolved_steps=(1,),
            signal_names=("V(out)",),
            trace_names=("V(out)",),
            components=("real",),
        )

    typed_monkeypatch.setattr(
        mcp_artifact_tools, "export_derived_raw_service", fake_export_derived_raw
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "export_derived_raw",
        raw_path="demo.qraw",
        signals=["V(out)"],
        output_path="derived.qraw",
        step=1,
        step_filters={"temp": 25},
        component="real",
        t_start=0.1,
        t_end=0.2,
    )

    assert result["plot_name"] == "Transient Analysis"
    assert result["trace_names"] == ["V(out)"]


def test_mcp_merge_waveforms_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_merge_waveforms(
        inputs: list[dict[str, object]],
        *,
        workspace_root: Path,
        output_path: str | None = None,
        all_steps: bool = False,
    ) -> MergedWaveformExport:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert inputs == [
            {"raw_path": "a.qraw", "signal": "V(out)", "label": "baseline"},
            {"raw_path": "b.qraw", "signal": "V(out)", "label": "candidate"},
        ]
        assert output_path == "merged.qraw"
        assert all_steps is False
        return MergedWaveformExport(
            source_raw_paths=(
                (tmp_path / "a.qraw").resolve(strict=False),
                (tmp_path / "b.qraw").resolve(strict=False),
            ),
            output_path=(tmp_path / "merged.qraw").resolve(strict=False),
            plot_name="Transient Analysis",
            axis_name="time",
            axis_trace_name="time",
            step=0,
            point_count=10,
            input_count=2,
            signal_names=("V(out)", "V(out)"),
            trace_names=("baseline", "candidate"),
            components=("real", "real"),
        )

    typed_monkeypatch.setattr(mcp_artifact_tools, "merge_waveforms_service", fake_merge_waveforms)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "merge_waveforms",
        inputs=[
            {"raw_path": "a.qraw", "signal": "V(out)", "label": "baseline"},
            {"raw_path": "b.qraw", "signal": "V(out)", "label": "candidate"},
        ],
        output_path="merged.qraw",
    )

    assert result["input_count"] == 2
    assert result["trace_names"] == ["baseline", "candidate"]


def test_mcp_compare_waveforms_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    manifest = tmp_path / "batch.json"
    manifest.write_text("{}", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_compare_waveforms(
        batch_path: str | Path,
        *,
        workspace_root: Path,
        signal: str,
        operation: str,
        baseline_run_index: int = 0,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: str = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> WaveformComparison:
        del step, step_filters, component, t_start, t_end
        assert workspace_root == tmp_path.resolve(strict=False)
        assert signal == "V(out)"
        assert operation == "max"
        assert baseline_run_index == 0
        return WaveformComparison(
            manifest_path=Path(batch_path).resolve(strict=False),
            batch_id="batch-a",
            sweep_kind="component_value",
            signal=signal,
            operation=operation,
            component="auto",
            baseline_run_index=0,
            baseline_run_label="R4=10",
            baseline_value=5.0,
            y_unit="V",
            run_count=2,
            compared_run_count=2,
            runs=(
                WaveformComparisonRun(
                    run_index=0,
                    run_label="R4=10",
                    assignment={"value": 10},
                    raw_path=(tmp_path / "a.qraw").resolve(strict=False),
                    step=0,
                    sample_count=100,
                    value=5.0,
                    delta_from_baseline=0.0,
                    percent_delta_from_baseline=0.0,
                ),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_artifact_tools, "compare_waveforms_service", fake_compare_waveforms
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "compare_waveforms", batch_path="batch.json", signal="V(out)", operation="max"
    )

    assert result["baseline_value"] == 5.0
    assert result["runs"][0]["run_label"] == "R4=10"


def test_mcp_read_component_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_read_component(
        schematic_path: str | Path, *, workspace_root: Path, reference: str
    ) -> ComponentRead:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        return ComponentRead(
            schematic_path=Path(schematic_path).resolve(strict=False),
            reference=reference,
            kind="R",
            value="1k",
            description="Resistor",
            nodes=("N001", "N002"),
            parameters={"tol": "1%"},
            raw_parameter_lines=(),
            position_x=100,
            position_y=200,
            rotation_degrees=0,
            has_subcircuit=False,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "read_component_service", fake_read_component)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("read_component", schematic_path="demo.qsch", reference="R1")

    assert result["reference"] == "R1"
    assert result["parameters"]["tol"] == "1%"


def test_mcp_read_component_symbol_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_read_component_symbol(
        schematic_path: str | Path, *, workspace_root: Path, reference: str
    ) -> ComponentSymbolRead:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        return ComponentSymbolRead(
            schematic_path=Path(schematic_path).resolve(strict=False),
            reference=reference,
            symbol_name="R",
            type_name="R",
            description="Resistor",
            library_file=None,
            shorted_pins=False,
            text_attributes=(
                SymbolTextMetadata(0, "reference", "R1", 100, 150, 1, 7, None, False, "0x1000000"),
            ),
            pins=(SymbolPinMetadata(0, "1", 0, 200, 0, 0, 1, 0, 0, "0x0", -1, None),),
            drawing_items=(
                SymbolDrawingMetadata(
                    0,
                    "line",
                    ("(0,200)", "(0,180)", "0", "0", "0x1000000", "-1", "-1"),
                    ((0, 200), (0, 180)),
                    (),
                ),
            ),
            drawing_tags=("line", "zigzag"),
            image_asset_tokens=(),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "read_component_symbol_service",
        fake_read_component_symbol,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("read_component_symbol", schematic_path="demo.qsch", reference="R1")

    assert result["reference"] == "R1"
    assert result["symbol_name"] == "R"
    assert result["drawing_items"][0]["tag_name"] == "line"
    assert result["pins"][0]["name"] == "1"


def test_mcp_add_component_symbol_drawing_is_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_component_symbol_drawing(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        tag_name: str,
        arguments: list[str],
        insert_index: int | None = None,
        output_path: str | Path | None = None,
    ) -> ComponentSymbolDrawingAdd:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert tag_name == "ellipse"
        assert arguments[0] == "(-150,150)"
        assert insert_index == 1
        return ComponentSymbolDrawingAdd(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            drawing_item=SymbolDrawingMetadata(
                1,
                "ellipse",
                tuple(arguments),
                ((-150, 150), (150, -150)),
                (),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "add_component_symbol_drawing_service",
        fake_add_component_symbol_drawing,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_component_symbol_drawing",
        schematic_path="demo.qsch",
        reference="R1",
        tag_name="ellipse",
        arguments=[
            "(-150,150)",
            "(150,-150)",
            "0",
            "0",
            "0",
            "0x1000000",
            "0x3000000",
            "-1",
            "-1",
        ],
        insert_index=1,
    )

    assert result["reference"] == "R1"
    assert result["drawing_item"]["index"] == 1
    assert result["drawing_item"]["tag_name"] == "ellipse"


def test_mcp_set_component_value_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_set_component_value(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        value: str | int | float | complex,
        output_path: str | Path | None = None,
    ) -> ComponentValueUpdate:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert value == "3.3k"
        return ComponentValueUpdate(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            value=str(value),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools, "set_component_value_service", fake_set_component_value
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_component_value", schematic_path="demo.qsch", reference="R1", value="3.3k"
    )

    assert result["reference"] == "R1"
    assert result["value"] == "3.3k"


def test_mcp_set_component_symbol_text_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_set_component_symbol_text(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        text_index: int | None = None,
        text_role: str | None = None,
        text: str | None = None,
        position_x: int | None = None,
        position_y: int | None = None,
        size: int | None = None,
        rotation_code: int | None = None,
        is_comment: bool | None = None,
        color_code: str | None = None,
        output_path: str | Path | None = None,
    ) -> ComponentSymbolTextUpdate:
        del text_index, output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert text_role == "value"
        assert text == "22k"
        assert position_x == 140
        assert position_y == -120
        assert size == 2
        assert rotation_code == 45
        assert is_comment is True
        assert color_code == "0x12ab34"
        return ComponentSymbolTextUpdate(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            text_attribute=SymbolTextMetadata(
                1,
                "value",
                "22k",
                140,
                -120,
                2,
                45,
                90,
                True,
                "0x12ab34",
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "set_component_symbol_text_service",
        fake_set_component_symbol_text,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_component_symbol_text",
        schematic_path="demo.qsch",
        reference="R1",
        text_role="value",
        text="22k",
        position_x=140,
        position_y=-120,
        size=2,
        rotation_code=45,
        is_comment=True,
        color_code="0x12ab34",
    )

    assert result["reference"] == "R1"
    assert result["text_attribute"]["text"] == "22k"
    assert result["text_attribute"]["rotation_degrees"] == 90


def test_mcp_set_component_symbol_drawing_is_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_set_component_symbol_drawing(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        drawing_index: int,
        tag_name: str | None = None,
        arguments: list[str] | None = None,
        output_path: str | Path | None = None,
    ) -> ComponentSymbolDrawingUpdate:
        del tag_name, output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert drawing_index == 2
        assert arguments is not None
        assert arguments[-3] == "0x12ab34"
        return ComponentSymbolDrawingUpdate(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            drawing_item=SymbolDrawingMetadata(
                2,
                "zigzag",
                tuple(arguments),
                ((-100, 180), (100, -180)),
                (),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "set_component_symbol_drawing_service",
        fake_set_component_symbol_drawing,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_component_symbol_drawing",
        schematic_path="demo.qsch",
        reference="R1",
        drawing_index=2,
        arguments=[
            "(-100,180)",
            "(100,-180)",
            "0",
            "0",
            "0",
            "0x12ab34",
            "-1",
            "-1",
        ],
    )

    assert result["reference"] == "R1"
    assert result["drawing_item"]["index"] == 2
    assert result["drawing_item"]["arguments"][-3] == "0x12ab34"


def test_mcp_set_component_symbol_pin_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_set_component_symbol_pin(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        new_pin_name: str | None = None,
        label_position_x: int | None = None,
        label_position_y: int | None = None,
        text_size: int | None = None,
        label_anchor_code: int | None = None,
        pin_kind_code: int | None = None,
        color_code: str | None = None,
        aux_code: int | None = None,
        behavioral_net_override: str | None = None,
        clear_behavioral_net_override: bool = False,
        output_path: str | Path | None = None,
    ) -> ComponentSymbolPinUpdate:
        del pin_name, text_size, color_code, aux_code, clear_behavioral_net_override, output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert pin_index == 0
        assert new_pin_name == "IN"
        assert label_position_x == 20
        assert label_position_y == 0
        assert label_anchor_code == 7
        assert pin_kind_code == 3
        assert behavioral_net_override == "VIN_OVERRIDE"
        return ComponentSymbolPinUpdate(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            pin=SymbolPinMetadata(
                0,
                "IN",
                0,
                200,
                20,
                0,
                1,
                7,
                3,
                "0x0",
                -1,
                "VIN_OVERRIDE",
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "set_component_symbol_pin_service",
        fake_set_component_symbol_pin,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_component_symbol_pin",
        schematic_path="demo.qsch",
        reference="R1",
        pin_index=0,
        new_pin_name="IN",
        label_position_x=20,
        label_position_y=0,
        label_anchor_code=7,
        pin_kind_code=3,
        behavioral_net_override="VIN_OVERRIDE",
    )

    assert result["reference"] == "R1"
    assert result["pin"]["name"] == "IN"
    assert result["pin"]["behavioral_net_override"] == "VIN_OVERRIDE"


def test_mcp_set_dll_block_pin_role_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_set_dll_block_pin_role(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        pin_role: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        output_path: str | Path | None = None,
    ) -> DllBlockPinRoleUpdate:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert pin_name == "in0"
        assert pin_index is None
        assert pin_role == "output"
        return DllBlockPinRoleUpdate(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            pin=SymbolPinMetadata(1, "in0", 600, -200, -150, -50, 0, 14, 146, "0x0", -1),
            input_pin_names=(),
            output_pin_names=("out0", "in0"),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "set_dll_block_pin_role_service",
        fake_set_dll_block_pin_role,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_dll_block_pin_role",
        schematic_path="demo.qsch",
        reference="X1",
        pin_name="in0",
        pin_role="output",
    )

    assert result["reference"] == "X1"
    assert result["pin"]["position_x"] == 600
    assert result["output_pin_names"] == ["out0", "in0"]


def test_mcp_remove_component_symbol_drawing_is_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_remove_component_symbol_drawing(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        drawing_index: int,
        output_path: str | Path | None = None,
    ) -> ComponentSymbolDrawingRemoval:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert drawing_index == 3
        return ComponentSymbolDrawingRemoval(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            drawing_item=SymbolDrawingMetadata(
                3,
                "ellipse",
                (
                    "(-150,150)",
                    "(150,-150)",
                    "0",
                    "0",
                    "0",
                    "0x1000000",
                    "0x3000000",
                    "-1",
                    "-1",
                ),
                ((-150, 150), (150, -150)),
                (),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "remove_component_symbol_drawing_service",
        fake_remove_component_symbol_drawing,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "remove_component_symbol_drawing",
        schematic_path="demo.qsch",
        reference="R1",
        drawing_index=3,
    )

    assert result["reference"] == "R1"
    assert result["drawing_item"]["index"] == 3
    assert result["drawing_item"]["tag_name"] == "ellipse"


def test_mcp_remove_dll_block_pin_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_remove_dll_block_pin(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        pin_index: int | None = None,
        pin_name: str | None = None,
        output_path: str | Path | None = None,
    ) -> RemovedDllBlockPin:
        del output_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "X1"
        assert pin_name == "clk"
        assert pin_index is None
        return RemovedDllBlockPin(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            removed_pin_name="clk",
            input_pin_names=("in0",),
            output_pin_names=("out0",),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "remove_dll_block_pin_service",
        fake_remove_dll_block_pin,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "remove_dll_block_pin",
        schematic_path="demo.qsch",
        reference="X1",
        pin_name="clk",
    )

    assert result["reference"] == "X1"
    assert result["removed_pin_name"] == "clk"
    assert result["input_pin_names"] == ["in0"]


def test_mcp_describe_live_gui_support_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_describe_live_gui_support(*, settings: QSpiceSettings) -> LiveGuiSupport:
        assert settings.workspace_root == tmp_path.resolve(strict=False)
        return LiveGuiSupport(
            windows_only=True,
            platform_supported=True,
            version_gated=True,
            external_bridge_required=True,
            session_manifest_scaffolding=True,
            qspice_executable_configured=True,
            notes=("live gui available",),
        )

    typed_monkeypatch.setattr(
        mcp_live_gui_tools,
        "describe_live_gui_support_service",
        fake_describe_live_gui_support,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("describe_live_gui_support")

    assert result["windows_only"] is True
    assert result["session_manifest_scaffolding"] is True


def test_mcp_open_schematic_in_gui_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_open_schematic_in_gui(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
    ) -> object:
        assert schematic_path == "demo.qsch"
        assert workspace_root == tmp_path.resolve(strict=False)
        return __import__(
            "qspice_mcp.services.live_gui.open_schematic_in_gui",
            fromlist=["OpenedSchematicInGui"],
        ).OpenedSchematicInGui(
            schematic_path=(tmp_path / "demo.qsch").resolve(strict=False),
            launcher="os_file_association",
            started=True,
            notes=("opened",),
        )

    typed_monkeypatch.setattr(
        mcp_live_gui_tools,
        "open_schematic_in_gui_service",
        fake_open_schematic_in_gui,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("open_schematic_in_gui", schematic_path="demo.qsch")

    assert result["schematic_path"].endswith("demo.qsch")
    assert result["launcher"] == "os_file_association"
    assert result["started"] is True


def test_mcp_refresh_schematic_in_gui_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_refresh_schematic_in_gui(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        settings: QSpiceSettings,
        strategy: str = "reopen_via_association",
        force_restart: bool = False,
    ) -> object:
        assert schematic_path == "demo.qsch"
        assert workspace_root == tmp_path.resolve(strict=False)
        assert settings.workspace_root == tmp_path.resolve(strict=False)
        assert strategy == "restart_qspice_and_reopen"
        assert force_restart is True
        return __import__(
            "qspice_mcp.services.live_gui.refresh_schematic_in_gui",
            fromlist=["RefreshedSchematicInGui"],
        ).RefreshedSchematicInGui(
            schematic_path=(tmp_path / "demo.qsch").resolve(strict=False),
            strategy="restart_qspice_and_reopen",
            started=True,
            qspice_process_restart_requested=True,
            qspice_process_restart_exit_code=0,
            notes=("refreshed",),
        )

    typed_monkeypatch.setattr(
        mcp_live_gui_tools,
        "refresh_schematic_in_gui_service",
        fake_refresh_schematic_in_gui,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "refresh_schematic_in_gui",
        schematic_path="demo.qsch",
        strategy="restart_qspice_and_reopen",
        force_restart=True,
    )

    assert result["schematic_path"].endswith("demo.qsch")
    assert result["strategy"] == "restart_qspice_and_reopen"
    assert result["qspice_process_restart_requested"] is True
    assert result["qspice_process_restart_exit_code"] == 0


def test_mcp_scaffold_live_gui_session_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_scaffold_live_gui_session(
        session_name: str,
        *,
        workspace_root: Path,
        settings: QSpiceSettings,
        schematic_path: str | Path | None = None,
        waveform_names: list[str] | None = None,
        cross_probe_signals: list[str] | None = None,
        output_path: str | Path | None = None,
    ) -> LiveGuiSessionScaffold:
        assert session_name == "buck-debug"
        assert workspace_root == tmp_path.resolve(strict=False)
        assert settings.workspace_root == tmp_path.resolve(strict=False)
        assert schematic_path == "demo.qsch"
        assert waveform_names == ["V(out)"]
        assert cross_probe_signals == ["V(out)"]
        assert output_path is None
        return LiveGuiSessionScaffold(
            session_name=session_name,
            manifest_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.json").resolve(
                strict=False
            ),
            schematic_path=(tmp_path / "demo.qsch").resolve(strict=False),
            launch_command=(
                str(executable.resolve(strict=False)),
                str((tmp_path / "demo.qsch").resolve(strict=False)),
            ),
            waveform_names=("V(out)",),
            cross_probe_signals=("V(out)",),
            notes=("bridge required",),
        )

    typed_monkeypatch.setattr(
        mcp_live_gui_tools,
        "scaffold_live_gui_session_service",
        fake_scaffold_live_gui_session,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "scaffold_live_gui_session",
        session_name="buck-debug",
        schematic_path="demo.qsch",
        waveform_names=["V(out)"],
        cross_probe_signals=["V(out)"],
    )

    assert result["session_name"] == "buck-debug"
    assert result["waveform_names"] == ["V(out)"]
    assert result["cross_probe_signals"] == ["V(out)"]


def test_mcp_live_gui_runtime_tools_are_invokable(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    class FakeLiveGuiManager:
        def __init__(self, settings: QSpiceSettings) -> None:
            self.settings = settings

        def launch_live_gui_session(self, **kwargs: object) -> object:
            assert kwargs["session_name"] == "buck-debug"
            assert kwargs["schematic_path"] == "demo.qsch"
            timestamp = __import__("datetime").datetime.now().astimezone()
            return __import__(
                "qspice_mcp.services.live_gui.launch_live_gui_session",
                fromlist=["LiveGuiSessionLaunch"],
            ).LiveGuiSessionLaunch(
                session_id="livegui-123456789abc",
                session_name="buck-debug",
                status="running",
                manifest_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.json").resolve(
                    strict=False
                ),
                output_root=(tmp_path / "artifacts" / "live_gui" / "buck-debug").resolve(
                    strict=False
                ),
                bridge_command=("bridge.exe", "manifest.json"),
                submitted_at=timestamp,
                bridge_pid=1234,
                notes=("bridge launched",),
            )

        def poll_live_gui_session(self, session_id: str) -> object:
            assert session_id == "livegui-123456789abc"
            timestamp = __import__("datetime").datetime.now().astimezone()
            return __import__(
                "qspice_mcp.services.live_gui.poll_live_gui_session",
                fromlist=["LiveGuiSessionStatus"],
            ).LiveGuiSessionStatus(
                session_id=session_id,
                session_name="buck-debug",
                status="completed",
                manifest_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.json").resolve(
                    strict=False
                ),
                output_root=(tmp_path / "artifacts" / "live_gui" / "buck-debug").resolve(
                    strict=False
                ),
                bridge_command=("bridge.exe", "manifest.json"),
                submitted_at=timestamp,
                completed_at=timestamp,
                bridge_pid=None,
                bridge_exit_code=0,
                duration_s=0.5,
                live_process_attached=False,
                stdout_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.stdout.log").resolve(
                    strict=False
                ),
                stderr_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.stderr.log").resolve(
                    strict=False
                ),
                error=None,
                notes=("completed",),
            )

        def send_live_gui_session_command(
            self,
            session_id: str,
            *,
            command: str,
            signal: str | None = None,
            payload: dict[str, object] | None = None,
        ) -> object:
            assert session_id == "livegui-123456789abc"
            assert command == "cross_probe_signal"
            assert signal == "V(out)"
            assert payload == {"waveform": "V(out)"}
            timestamp = __import__("datetime").datetime.now().astimezone()
            return __import__(
                "qspice_mcp.services.live_gui.send_live_gui_session_command",
                fromlist=["LiveGuiSessionCommandDispatch"],
            ).LiveGuiSessionCommandDispatch(
                session_id=session_id,
                command_id=1,
                command=command,
                signal=signal,
                payload={} if payload is None else payload,
                queued_at=timestamp,
                command_path=(
                    tmp_path / "artifacts" / "live_gui" / "buck-debug" / "bridge.commands.jsonl"
                ).resolve(strict=False),
                note="queued",
            )

        def poll_live_gui_session_events(
            self,
            session_id: str,
            *,
            after_sequence: int = 0,
            limit: int = 50,
        ) -> object:
            assert session_id == "livegui-123456789abc"
            assert after_sequence == 0
            assert limit == 5
            timestamp = __import__("datetime").datetime.now().astimezone()
            events_module = __import__(
                "qspice_mcp.services.live_gui.poll_live_gui_session_events",
                fromlist=["LiveGuiSessionEvent", "LiveGuiSessionEventPoll"],
            )
            return events_module.LiveGuiSessionEventPoll(
                session_id=session_id,
                status="running",
                event_path=(
                    tmp_path / "artifacts" / "live_gui" / "buck-debug" / "bridge.events.jsonl"
                ).resolve(strict=False),
                next_sequence=1,
                events=(
                    events_module.LiveGuiSessionEvent(
                        sequence=1,
                        event="command_ack",
                        created_at=timestamp,
                        signal="V(out)",
                        payload={"waveform": "V(out)"},
                    ),
                ),
                live_process_attached=True,
                notes=(),
            )

        def close_live_gui_session(
            self,
            session_id: str,
            *,
            delete_manifest: bool = False,
        ) -> object:
            assert session_id == "livegui-123456789abc"
            assert delete_manifest is True
            return __import__(
                "qspice_mcp.services.live_gui.close_live_gui_session",
                fromlist=["LiveGuiSessionClosure"],
            ).LiveGuiSessionClosure(
                session_id=session_id,
                status="closed",
                output_root=(tmp_path / "artifacts" / "live_gui" / "buck-debug").resolve(
                    strict=False
                ),
                manifest_path=(tmp_path / "artifacts" / "live_gui" / "buck-debug.json").resolve(
                    strict=False
                ),
                bridge_terminated=True,
                manifest_deleted=True,
                note="Closed live GUI session.",
            )

    typed_monkeypatch.setattr(mcp_runtime, "LiveGuiSessionManager", FakeLiveGuiManager)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    launch_result = server.invoke_tool(
        "launch_live_gui_session",
        session_name="buck-debug",
        schematic_path="demo.qsch",
    )
    poll_result = server.invoke_tool(
        "poll_live_gui_session",
        session_id="livegui-123456789abc",
    )
    command_result = server.invoke_tool(
        "send_live_gui_session_command",
        session_id="livegui-123456789abc",
        command="cross_probe_signal",
        signal="V(out)",
        payload={"waveform": "V(out)"},
    )
    events_result = server.invoke_tool(
        "poll_live_gui_session_events",
        session_id="livegui-123456789abc",
        after_sequence=0,
        limit=5,
    )
    close_result = server.invoke_tool(
        "close_live_gui_session",
        session_id="livegui-123456789abc",
        delete_manifest=True,
    )

    assert launch_result["status"] == "running"
    assert poll_result["status"] == "completed"
    assert command_result["command_id"] == 1
    assert events_result["events"][0]["event"] == "command_ack"
    assert close_result["status"] == "closed"


def test_mcp_run_value_sweep_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_run_value_sweep(
        source_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        values: list[str | int | float],
        settings: QSpiceSettings | None = None,
        output_dir: str | Path | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: tuple[str, ...] = (),
        resume: bool = False,
        retained_artifact_policy: str = "cleanup",
    ) -> SimulationBatch:
        del settings, output_dir, parallelism, dry_run, timeout_s, ascii_raw, extra_switches
        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert values == [1, 2]
        assert resume is True
        assert retained_artifact_policy == "keep_orphans"
        return SimulationBatch(
            source_path=Path(source_path).resolve(strict=False),
            output_root=(tmp_path / "artifacts").resolve(strict=False),
            sweep_kind="component_value",
            run_count=2,
            parallelism=1,
            sequential=True,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="R1=1",
                    assignment={"R1": 1},
                    schematic_path=(tmp_path / "run-000.qsch").resolve(strict=False),
                    netlist_path=(tmp_path / "run-000.net").resolve(strict=False),
                    log_path=(tmp_path / "run-000.log").resolve(strict=False),
                    raw_path=(tmp_path / "run-000.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "run-000.net"),
                    dry_run=False,
                    exit_code=0,
                    duration_s=0.1,
                ),
            ),
            reference=reference,
        )

    typed_monkeypatch.setattr(mcp_simulation_tools, "run_value_sweep_service", fake_run_value_sweep)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "run_value_sweep",
        source_path="demo.qsch",
        reference="R1",
        values=[1, 2],
        resume=True,
        retained_artifact_policy="keep_orphans",
    )

    assert result["run_count"] == 2
    assert result["reference"] == "R1"
    assert result["runs"][0]["assignment"]["R1"] == 1


def test_mcp_submit_batch_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    class FakeBatchManager:
        def __init__(self, settings: QSpiceSettings) -> None:
            self.settings = settings

        def submit_batch(self, **kwargs: object) -> BatchSubmission:
            assert kwargs["batch_kind"] == "component_value"
            assert kwargs["resume"] is True
            assert kwargs["retained_artifact_policy"] == "keep_all"
            return BatchSubmission(
                batch_id="batch-123",
                batch_kind="component_value",
                status="queued",
                source_path=(tmp_path / "demo.qsch").resolve(strict=False),
                output_root=(tmp_path / "artifacts").resolve(strict=False),
                manifest_path=(tmp_path / "artifacts" / "batch.json").resolve(strict=False),
                submitted_at=__import__("datetime").datetime.now().astimezone(),
            )

        def get_batch_status(self, batch_id: str) -> object:
            raise AssertionError(batch_id)

        def collect_batch_results(self, batch_id: str) -> object:
            raise AssertionError(batch_id)

        def cancel_batch(self, batch_id: str) -> object:
            raise AssertionError(batch_id)

    typed_monkeypatch.setattr(mcp_runtime, "SimulationBatchManager", FakeBatchManager)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "submit_batch",
        batch_kind="component_value",
        source_path="demo.qsch",
        reference="R1",
        values=[1, 2],
        resume=True,
        retained_artifact_policy="keep_all",
    )

    assert result["batch_id"] == "batch-123"
    assert result["status"] == "queued"


def test_mcp_remote_session_tools_are_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    class FakeRemoteManager:
        def __init__(self, settings: QSpiceSettings) -> None:
            self.settings = settings

        def submit_remote_simulation(self, **kwargs: object) -> RemoteSimulationSubmission:
            assert kwargs["source_path"] == "demo.qsch"
            assert kwargs["dry_run"] is True
            return RemoteSimulationSubmission(
                session_id="remote-123",
                status="queued",
                source_path=(tmp_path / "demo.qsch").resolve(strict=False),
                output_root=(tmp_path / "artifacts").resolve(strict=False),
                submitted_at=__import__("datetime").datetime.now().astimezone(),
                owner_host_id="host-a",
            )

        def poll_remote_run(self, session_id: str) -> RemoteRunStatus:
            assert session_id == "remote-123"
            artifact_root = (tmp_path / "artifacts").resolve(strict=False)
            timestamp = __import__("datetime").datetime.now().astimezone()
            return RemoteRunStatus(
                session_id=session_id,
                status="completed",
                source_path=(tmp_path / "demo.qsch").resolve(strict=False),
                output_root=artifact_root,
                submitted_at=timestamp,
                completed_at=timestamp,
                simulation_input_path=(artifact_root / "demo.net").resolve(strict=False),
                log_path=(artifact_root / "demo.log").resolve(strict=False),
                raw_path=(artifact_root / "demo.qraw").resolve(strict=False),
                bundle_path=(artifact_root / "bundle.zip").resolve(strict=False),
                dry_run=True,
                exit_code=0,
                duration_s=0.1,
                log_available=True,
                raw_available=True,
                bundle_available=True,
                owner_host_id="host-a",
            )

        def download_remote_artifacts(
            self,
            session_id: str,
            *,
            output_path: str | None = None,
            artifact_kinds: list[str] | None = None,
        ) -> RemoteArtifactDownload:
            assert session_id == "remote-123"
            assert output_path == "bundle.zip"
            assert artifact_kinds == ["summary", "raw"]
            return RemoteArtifactDownload(
                session_id=session_id,
                status="completed",
                output_path=(tmp_path / "bundle.zip").resolve(strict=False),
                artifact_kinds=("summary", "raw"),
                entry_names=("session.json", "artifacts/demo.qraw"),
                artifact_count=2,
                bundle_size_bytes=256,
            )

        def close_remote_session(
            self,
            session_id: str,
            *,
            delete_bundle: bool = False,
        ) -> RemoteSessionClosure:
            assert session_id == "remote-123"
            assert delete_bundle is True
            return RemoteSessionClosure(
                session_id=session_id,
                status="closed",
                output_root=(tmp_path / "artifacts").resolve(strict=False),
                bundle_deleted=True,
                note="Remote session closed.",
            )

    typed_monkeypatch.setattr(mcp_runtime, "RemoteSimulationManager", FakeRemoteManager)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    submit_result = server.invoke_tool(
        "submit_remote_simulation",
        source_path="demo.qsch",
        dry_run=True,
    )
    poll_result = server.invoke_tool("poll_remote_run", session_id="remote-123")
    download_result = server.invoke_tool(
        "download_remote_artifacts",
        session_id="remote-123",
        output_path="bundle.zip",
        artifact_kinds=["summary", "raw"],
    )
    close_result = server.invoke_tool(
        "close_remote_session",
        session_id="remote-123",
        delete_bundle=True,
    )

    assert submit_result["session_id"] == "remote-123"
    assert submit_result["status"] == "queued"
    assert submit_result["owner_host_id"] == "host-a"
    assert poll_result["status"] == "completed"
    assert poll_result["bundle_available"] is True
    assert download_result["artifact_count"] == 2
    assert close_result["status"] == "closed"


def test_mcp_add_and_remove_instruction_are_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_add_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
    ) -> InstructionAdd:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert instruction == ".tran 5m"
        return InstructionAdd(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "added.qsch").resolve(strict=False),
            instruction=instruction,
        )

    def fake_remove_instruction(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        instruction: str,
        output_path: str | Path | None = None,
        regex: bool = False,
    ) -> InstructionRemoval:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert regex is True
        return InstructionRemoval(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "removed.qsch").resolve(strict=False),
            instruction=instruction,
            regex=regex,
        )

    typed_monkeypatch.setattr(mcp_schematic_tools, "add_instruction_service", fake_add_instruction)
    typed_monkeypatch.setattr(
        mcp_schematic_tools, "remove_instruction_service", fake_remove_instruction
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    added = server.invoke_tool(
        "add_instruction", schematic_path="demo.qsch", instruction=".tran 5m"
    )
    removed = server.invoke_tool(
        "remove_instruction",
        schematic_path="demo.qsch",
        instruction=r"\.AC.*",
        regex=True,
    )

    assert added["instruction"] == ".tran 5m"
    assert removed["regex"] is True


def test_mcp_save_schematic_as_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_save_schematic_as(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        output_path: str | Path,
    ) -> SavedSchematic:
        assert workspace_root == tmp_path.resolve(strict=False)
        return SavedSchematic(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(workspace_root / Path(output_path)).resolve(strict=False),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools, "save_schematic_as_service", fake_save_schematic_as
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "save_schematic_as", schematic_path="demo.qsch", output_path="copy.qsch"
    )

    assert result["output_path"] == str((tmp_path / "copy.qsch").resolve(strict=False))


def test_mcp_read_measures_accepts_step_filters(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text("", encoding="utf-8")
    calls: list[dict[str, object] | None] = []
    typed_monkeypatch = monkeypatch

    def fake_read_measures(
        log_path: str | Path,
        *,
        workspace_root: Path,
        settings: QSpiceSettings | None = None,
        measures: list[str] | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        refresh_measures: bool = True,
        meas_path: str | Path | None = None,
    ) -> MeasureRead:
        del settings, step, refresh_measures, meas_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert measures == ["delay"]
        calls.append(step_filters)
        return MeasureRead(
            log_path=Path(log_path).resolve(strict=False),
            meas_path=(tmp_path / "demo.meas").resolve(strict=False),
            step_count=2,
            resolved_step=1,
            measures=(
                MeasureResult(
                    name="delay",
                    analysis="tran",
                    expression="TRIG V(out)",
                    value_columns=("delay", "delay_1"),
                    rows=(MeasureRow(step=1, values={"delay": 0.3, "delay_1": 0.4}),),
                ),
            ),
        )

    typed_monkeypatch.setattr(mcp_waveform_tools, "read_measures_service", fake_read_measures)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "read_measures",
        log_path="demo.log",
        measures=["delay"],
        step_filters={"vin": 12},
    )

    assert calls == [{"vin": 12}]
    assert result["resolved_step"] == 1
    assert result["measures"][0]["rows"][0]["values"]["delay_1"] == 0.4


def test_mcp_rename_component_reference_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_rename_component_reference(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        new_reference: str,
        output_path: str | Path | None = None,
    ) -> object:
        from qspice_mcp.services.schematic.rename_component_reference import (  # noqa: PLC0415
            RenamedComponentReference,
        )

        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert new_reference == "R2"
        return RenamedComponentReference(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
            new_reference=new_reference,
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "rename_component_reference_service",
        fake_rename_component_reference,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "rename_component_reference",
        schematic_path="demo.qsch",
        reference="R1",
        new_reference="R2",
    )

    assert result["reference"] == "R1"
    assert result["new_reference"] == "R2"


def test_mcp_describe_edit_capability_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_describe_edit_capability(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        intent: str,
    ) -> object:
        from qspice_mcp.services.schematic.describe_edit_capability import (  # noqa: PLC0415
            EditCapability,
        )

        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        assert intent == "change_value"
        return EditCapability(
            schematic_path=Path(schematic_path).resolve(strict=False),
            reference=reference,
            component_kind="R",
            intent=intent,
            supported=True,
            suggested_tool="set_component_value",
            suggested_parameters={
                "schematic_path": str(schematic_path),
                "reference": "R1",
                "value": "1k",
            },
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "describe_edit_capability_service",
        fake_describe_edit_capability,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "describe_edit_capability",
        schematic_path="demo.qsch",
        reference="R1",
        intent="change_value",
    )

    assert result["supported"] is True
    assert result["suggested_tool"] == "set_component_value"


def test_mcp_describe_schematic_edit_support_is_invokable(
    monkeypatch: object, tmp_path: Path
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_describe_support() -> object:
        from qspice_mcp.services.schematic.describe_schematic_edit_support import (  # noqa: PLC0415
            IntentEntry,
            SchematicEditSupport,
        )

        return SchematicEditSupport(
            supported_intents=(
                IntentEntry(
                    intent="rename_reference",
                    label="Rename",
                    tool="rename_component_reference",
                    supported=True,
                    requires_backend=False,
                    preconditions=(),
                    limitations=(),
                ),
            ),
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "describe_schematic_edit_support_service",
        fake_describe_support,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("describe_schematic_edit_support")

    assert len(result["supported_intents"]) == 1
    assert result["supported_intents"][0]["intent"] == "rename_reference"


def test_mcp_remove_component_is_invokable(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch

    def fake_remove_component(
        schematic_path: str | Path,
        *,
        workspace_root: Path,
        reference: str,
        output_path: str | Path | None = None,
    ) -> object:
        from qspice_mcp.services.schematic.remove_component import RemovedComponent  # noqa: PLC0415

        assert workspace_root == tmp_path.resolve(strict=False)
        assert reference == "R1"
        return RemovedComponent(
            schematic_path=Path(schematic_path).resolve(strict=False),
            output_path=(tmp_path / "edited.qsch").resolve(strict=False),
            reference=reference,
        )

    typed_monkeypatch.setattr(
        mcp_schematic_tools,
        "remove_component_service",
        fake_remove_component,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "remove_component",
        schematic_path="demo.qsch",
        reference="R1",
    )

    assert result["reference"] == "R1"
