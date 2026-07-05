"""Tests for mixed-signal custom-device scaffold services."""

from __future__ import annotations

import importlib
from importlib.resources import files
from pathlib import Path

import pytest

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.subprocess import SubprocessResult
from qspice_mcp.services._backends.schematic_editor import (
    ComponentSymbolMetadata,
    SymbolPinMetadata,
)
from qspice_mcp.services._internals.dll_contracts import parse_dll_source_contract_text
from qspice_mcp.services.mixed_signal._dll_toolchain_probe import (
    describe_dll_build_toolchain,
    dll_build_degradation_hints,
    find_bundled_dmc,
)
from qspice_mcp.services.mixed_signal.build_dll_device import build_dll_device
from qspice_mcp.services.mixed_signal.describe_mixed_signal_support import (
    describe_mixed_signal_support,
)
from qspice_mcp.services.mixed_signal.scaffold_dll_device import scaffold_dll_device
from qspice_mcp.services.mixed_signal.scaffold_dll_device_from_symbol import (
    scaffold_dll_device_from_symbol,
)
from qspice_mcp.services.mixed_signal.scaffold_python_device import (
    scaffold_python_device,
)
from qspice_mcp.services.mixed_signal.scaffold_socket_device import (
    scaffold_socket_device,
)
from qspice_mcp.services.mixed_signal.scaffold_verilog_device import (
    scaffold_verilog_device,
)
from qspice_mcp.services.mixed_signal.validate_dll_symbol_signature import (
    validate_dll_symbol_signature,
)

_validation_dll_symbol_signature_service = importlib.import_module(
    "qspice_mcp.services.mixed_signal.validate_dll_symbol_signature"
)
_scaffold_dll_device_from_symbol_service = importlib.import_module(
    "qspice_mcp.services.mixed_signal.scaffold_dll_device_from_symbol"
)

# ---------------------------------------------------------------------------
# describe_mixed_signal_support
# ---------------------------------------------------------------------------


def test_describe_mixed_signal_support_returns_all_true(tmp_path) -> None:
    settings = QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=tmp_path)

    result = describe_mixed_signal_support(settings=settings)

    assert result.dll_device_scaffolding is True
    assert result.verilog_device_scaffolding is True
    assert result.socket_device_scaffolding is True
    assert result.python_device_scaffolding is True
    assert any("scaffold_dll_device" in note for note in result.notes)


# ---------------------------------------------------------------------------
# scaffold_dll_device
# ---------------------------------------------------------------------------


def test_scaffold_dll_device_writes_cpp_and_cmake(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_dll_device(
        "MyAmp",
        workspace_root=workspace,
        settings=None,
    )

    assert result.device_name == "MyAmp"
    assert result.source_path.suffix == ".cpp"
    assert result.source_path.is_file()
    assert result.cmake_path.is_file()
    assert result.cmake_path.name == "CMakeLists.txt"
    assert result.source_line_count > 10
    assert result.cmake_line_count > 3

    source_text = result.source_path.read_text(encoding="utf-8")
    assert "dll_device_count" in source_text
    assert "dll_device(" in source_text
    assert "dll_device_end" in source_text
    assert "MyAmp" in source_text

    cmake_text = result.cmake_path.read_text(encoding="utf-8")
    assert "project(MyAmp" in cmake_text
    assert "add_library" in cmake_text

    assert any("cl /LD" in note for note in result.notes)
    assert any("QSpice" in note for note in result.notes)


def test_scaffold_dll_device_rejects_numeric_leading_name(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="device_name must start with a letter"):
        scaffold_dll_device("123BadName", workspace_root=workspace, settings=None)


def test_scaffold_dll_device_sanitizes_special_characters(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_dll_device(
        "My Device!",
        workspace_root=workspace,
        settings=None,
    )

    assert result.source_path.is_file()
    source_text = result.source_path.read_text(encoding="utf-8")
    assert "My Device!" in source_text  # device_name preserved in comments
    assert "_" in result.source_path.name  # safe_name has underscores


def test_scaffold_dll_device_places_next_to_schematic_when_requested(
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    schematic = workspace / "subdir" / "demo.qsch"
    schematic.parent.mkdir(parents=True)
    schematic.write_text("schematic", encoding="utf-8")

    result = scaffold_dll_device(
        "MyAmp",
        workspace_root=workspace,
        settings=None,
        schematic_path=schematic,
    )

    assert result.source_path.is_file()
    assert result.cmake_path.is_file()
    assert result.source_path.parent == schematic.parent.resolve(strict=False)
    assert result.cmake_path.parent == schematic.parent.resolve(strict=False)


def test_parse_dll_source_contract_text_reads_buck_style_export_and_pins() -> None:
    bundle = (
        files("qspice_mcp.data.recipes")
        / "non_isolated_dc_dc"
        / "buck_converter_cpp"
        / "buck_controller.cpp"
    )
    source_text = bundle.read_text(encoding="utf-8")

    contract = parse_dll_source_contract_text(
        source_text,
        source_path=Path("buck_controller.cpp"),
    )

    assert contract.primary_export_name == "buck_controller"
    assert contract.exported_function_names == ("buck_controller",)
    assert contract.input_pin_names == ("in0", "in1", "in2", "in3", "in4")
    assert contract.output_pin_names == ("out0", "out1", "out2", "out3", "out4")
    assert contract.warnings == ()


def test_validate_dll_symbol_signature_reports_matching_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    class FakeEditor:
        def get_component_value(self, reference: str) -> str:
            assert reference == "X1"
            return "Buck_controller"

    source_path = tmp_path / "buck_controller.cpp"
    source_path.write_text(
        (
            files("qspice_mcp.data.recipes")
            / "non_isolated_dc_dc"
            / "buck_converter_cpp"
            / "buck_controller.cpp"
        ).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        _validation_dll_symbol_signature_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _validation_dll_symbol_signature_service,
        "read_component_symbol_metadata",
        lambda editor, *, reference: ComponentSymbolMetadata(
            symbol_name="",
            type_name="Ø(.DLL)",
            description=None,
            library_file=None,
            shorted_pins=False,
            text_attributes=(),
            pins=tuple(
                SymbolPinMetadata(
                    index, name, -800, -(index * 200), 150, -50, 0, 14, 145, "0x0", -1
                )
                for index, name in enumerate(("in0", "in1", "in2", "in3", "in4"))
            )
            + tuple(
                SymbolPinMetadata(
                    index + 5, name, 600, -(index * 200), -150, -50, 0, 14, 146, "0x0", -1
                )
                for index, name in enumerate(("out0", "out1", "out2", "out3", "out4"))
            ),
            drawing_items=(),
            drawing_tags=(),
            image_asset_tokens=(),
        ),
    )

    result = validate_dll_symbol_signature(
        tmp_path / "demo.qsch",
        workspace_root=tmp_path,
        reference="X1",
        source_path=source_path,
    )

    assert result.is_valid is True
    assert result.matched_export_name == "buck_controller"
    assert result.symbol_input_pin_names == ("in0", "in1", "in2", "in3", "in4")
    assert result.source_output_pin_names == ("out0", "out1", "out2", "out3", "out4")
    assert result.mismatches == ()


def test_validate_dll_symbol_signature_reports_pin_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    class FakeEditor:
        def get_component_value(self, reference: str) -> str:
            assert reference == "X1"
            return "Buck_controller"

    source_path = tmp_path / "buck_controller.cpp"
    source_path.write_text(
        'extern "C" __declspec(dllexport) void buck_controller(\n'
        "    void **opaque,\n"
        "    double t,\n"
        "    union uData *data\n"
        ") {\n"
        "    double in0 = data[0].d; // input\n"
        "    double &out0 = data[1].d; // output\n"
        "}\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        _validation_dll_symbol_signature_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _validation_dll_symbol_signature_service,
        "read_component_symbol_metadata",
        lambda editor, *, reference: ComponentSymbolMetadata(
            symbol_name="",
            type_name="Ø(.DLL)",
            description=None,
            library_file=None,
            shorted_pins=False,
            text_attributes=(),
            pins=(
                SymbolPinMetadata(0, "in0", -800, 0, 150, -50, 0, 14, 145, "0x0", -1),
                SymbolPinMetadata(1, "clk", -800, -200, 150, -50, 0, 14, 145, "0x0", -1),
                SymbolPinMetadata(2, "out0", 600, 0, -150, -50, 0, 14, 146, "0x0", -1),
            ),
            drawing_items=(),
            drawing_tags=(),
            image_asset_tokens=(),
        ),
    )

    result = validate_dll_symbol_signature(
        tmp_path / "demo.qsch",
        workspace_root=tmp_path,
        reference="X1",
        source_path=source_path,
    )

    assert result.is_valid is False
    assert any("Pin count mismatch" in mismatch for mismatch in result.mismatches)


def test_scaffold_dll_device_from_symbol_writes_contract_matched_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    class FakeEditor:
        def get_component_value(self, reference: str) -> str:
            assert reference == "X1"
            return "Buck_controller"

    monkeypatch.setattr(
        _scaffold_dll_device_from_symbol_service,
        "open_schematic_editor",
        lambda schematic_path, *, workspace_root: (
            FakeEditor(),
            Path(schematic_path).resolve(strict=False),
            "fake",
        ),
    )
    monkeypatch.setattr(
        _scaffold_dll_device_from_symbol_service,
        "read_component_symbol_metadata",
        lambda editor, *, reference: ComponentSymbolMetadata(
            symbol_name="",
            type_name="Ø(.DLL)",
            description=None,
            library_file=None,
            shorted_pins=False,
            text_attributes=(),
            pins=(
                SymbolPinMetadata(0, "in0", -800, 0, 150, -50, 0, 14, 145, "0x0", -1),
                SymbolPinMetadata(1, "clk", -800, -200, 150, -50, 0, 14, 145, "0x0", -1),
                SymbolPinMetadata(2, "pwm", 600, 0, -150, -50, 0, 14, 146, "0x0", -1),
            ),
            drawing_items=(),
            drawing_tags=(),
            image_asset_tokens=(),
        ),
    )

    result = scaffold_dll_device_from_symbol(
        workspace / "demo.qsch",
        workspace_root=workspace,
        settings=None,
        reference="X1",
    )

    assert result.device_name == "Buck_controller"
    assert result.export_name == "Buck_controller"
    assert result.input_pin_names == ("in0", "clk")
    assert result.output_pin_names == ("pwm",)
    assert result.source_path.is_file()
    assert result.cmake_path.is_file()
    # Auto-placed next to schematic for QSPICE Show Source
    assert result.source_path.parent == workspace.resolve(strict=False)
    assert result.cmake_path.parent == workspace.resolve(strict=False)

    source_text = result.source_path.read_text(encoding="utf-8")
    assert "#undef in0" in source_text
    assert 'extern "C" __declspec(dllexport) void Buck_controller' in source_text
    assert "double in0 = data[0].d; // input" in source_text
    assert "double &pwm = data[2].d; // output" in source_text

    assert any("Avoid shared global mutable state" in note for note in result.notes)


# ---------------------------------------------------------------------------
# scaffold_verilog_device
# ---------------------------------------------------------------------------


def test_scaffold_verilog_device_writes_module(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_verilog_device(
        "my_i2c_slave",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
    )

    assert result.device_name == "my_i2c_slave"
    assert result.output_path.suffix == ".v"
    assert result.output_path.is_file()
    assert result.line_count > 5

    text = result.output_path.read_text(encoding="utf-8")
    assert "module my_i2c_slave" in text
    assert "input  wire a" in text
    assert "output wire y" in text
    assert "endmodule" in text

    assert any("Verilog Device" in note for note in result.notes)
    assert any("File=" in note for note in result.notes)


def test_scaffold_verilog_device_rejects_numeric_start(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="must start with a letter"):
        scaffold_verilog_device(
            "7seg",
            workspace_root=workspace,
            settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
        )


def test_scaffold_verilog_device_accepts_underscore_start(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_verilog_device(
        "_private_module",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
    )

    assert result.output_path.is_file()
    text = result.output_path.read_text(encoding="utf-8")
    assert "module private_module" in text  # leading _ stripped for module name


# ---------------------------------------------------------------------------
# scaffold_socket_device
# ---------------------------------------------------------------------------


def test_scaffold_socket_device_writes_server(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_socket_device(
        "TemperatureSensor",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
    )

    assert result.device_name == "TemperatureSensor"
    assert result.output_path.suffix == ".py"
    assert result.output_path.is_file()
    assert result.line_count > 20

    text = result.output_path.read_text(encoding="utf-8")
    assert "TemperatureSensor" in text
    assert "def compute_currents(" in text
    assert "def serve(" in text
    assert "socket.AF_INET" in text
    assert "argparse" in text

    assert any("--port" in note for note in result.notes)
    assert any("Socket Device" in note for note in result.notes)


def test_scaffold_socket_device_rejects_empty_name(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="device_name must produce a non-empty"):
        scaffold_socket_device(
            "",
            workspace_root=workspace,
            settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
        )


# ---------------------------------------------------------------------------
# scaffold_python_device
# ---------------------------------------------------------------------------


def test_scaffold_python_device_writes_server(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_python_device(
        "MyLogicGate",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
    )

    assert result.device_name == "MyLogicGate"
    assert result.output_path.suffix == ".py"
    assert result.output_path.is_file()
    assert result.line_count > 15

    text = result.output_path.read_text(encoding="utf-8")
    assert "MyLogicGate" in text
    assert "def compute(" in text
    assert "def serve()" in text
    assert "sys.stdin.readline()" in text

    assert any("Python Device" in note for note in result.notes)


def test_scaffold_python_device_rejects_empty_name(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(ValueError, match="device_name must produce a non-empty"):
        scaffold_python_device(
            "",
            workspace_root=workspace,
            settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
        )


def test_scaffold_python_device_custom_output_path(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = scaffold_python_device(
        "Gate",
        workspace_root=workspace,
        settings=QSpiceSettings(exe=tmp_path / "QSPICE64.exe", workspace_root=workspace),
        output_path="subdir/my_gate.py",
    )

    assert result.output_path.name == "my_gate.py"
    assert result.output_path.is_file()


# ---------------------------------------------------------------------------
# build_dll_device
# ---------------------------------------------------------------------------


def _fake_qspice_install(root: Path) -> Path:
    qspice_exe = root / "QSPICE" / "QSPICE64.exe"
    dmc_exe = root / "QSPICE" / "dm" / "bin" / "dmc.exe"
    qspice_exe.parent.mkdir(parents=True, exist_ok=True)
    qspice_exe.write_text("", encoding="utf-8")
    dmc_exe.parent.mkdir(parents=True, exist_ok=True)
    dmc_exe.write_bytes(b"MZ")
    return qspice_exe


def test_find_bundled_dmc_from_qspice_exe(tmp_path: Path) -> None:
    qspice_exe = _fake_qspice_install(tmp_path)
    resolved = find_bundled_dmc(qspice_exe)
    assert resolved is not None
    assert resolved.name == "dmc.exe"
    assert resolved.parent.name == "bin"


def test_auto_prefers_dmc_when_qspice_resolves(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "buck_controller.cpp"
    source.write_text("// test source\n", encoding="utf-8")
    output = workspace / "buck_controller.dll"
    output.write_bytes(b"MZ")
    qspice_exe = _fake_qspice_install(tmp_path)

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: None)

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_s: float | None,
        env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        assert command[1:5] == ("-mn", "-WD", "buck_controller.cpp", "kernel32.lib")
        assert cwd == workspace
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.run_subprocess",
        fake_run,
    )

    result = build_dll_device(
        source,
        workspace_root=workspace,
        toolchain="auto",
        qspice_executable=qspice_exe,
    )

    assert result.toolchain == "dmc"
    assert result.output_path == output


def test_build_dll_device_invokes_dmc_with_dm_bin_on_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "device.cpp"
    source.write_text("// test\n", encoding="utf-8")
    output = workspace / "device.dll"
    output.write_bytes(b"MZ")
    qspice_exe = _fake_qspice_install(tmp_path)
    dm_bin = str(qspice_exe.parent / "dm" / "bin")

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: None)

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_s: float | None,
        env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        assert env is not None
        assert env["PATH"].startswith(dm_bin)
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.05,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.run_subprocess",
        fake_run,
    )

    result = build_dll_device(
        source,
        workspace_root=workspace,
        toolchain="dmc",
        qspice_executable=qspice_exe,
    )

    assert result.toolchain == "dmc"
    assert result.output_path == output


def test_explicit_dmc_errors_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "device.cpp"
    source.write_text("// x\n", encoding="utf-8")

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.discover_executable",
        lambda _exe: (None, "unavailable"),
    )

    with pytest.raises(BackendUnavailableError, match="QSpice-bundled DMC was not found"):
        build_dll_device(
            source,
            workspace_root=workspace,
            toolchain="dmc",
            qspice_executable=None,
        )


def test_build_dll_device_invokes_msvc_and_returns_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "buck_controller.cpp"
    source.write_text("// test source\n", encoding="utf-8")
    output = workspace / "buck_controller.dll"
    output.write_bytes(b"MZ")

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: "cl")

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_s: float | None,
        env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        assert command[0] == "cl"
        assert cwd == workspace
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.run_subprocess",
        fake_run,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_bundled_dmc",
        lambda _exe: None,
    )

    result = build_dll_device(
        source,
        workspace_root=workspace,
        toolchain="msvc",
    )

    assert result.toolchain == "msvc"
    assert result.output_path == output
    assert result.exit_code == 0


def test_build_dll_device_surfaces_compiler_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "bad.cpp"
    source.write_text("// bad\n", encoding="utf-8")

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: "cl")

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_s: float | None,
        env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=2,
            duration_s=0.2,
            stdout="",
            stderr="error C2065",
        )

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.run_subprocess",
        fake_run,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_bundled_dmc",
        lambda _exe: None,
    )

    with pytest.raises(ValidationError, match="DLL build failed"):
        build_dll_device(source, workspace_root=workspace, toolchain="msvc")


def test_build_dll_device_reports_missing_toolchain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "device.cpp"
    source.write_text("// x\n", encoding="utf-8")

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: None)
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.find_bundled_dmc",
        lambda _exe: None,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.find_vcvars64_bat",
        lambda: None,
    )

    with pytest.raises(BackendUnavailableError, match="No supported DLL build toolchain"):
        build_dll_device(source, workspace_root=workspace, toolchain="auto")


@pytest.mark.integration
def test_build_dll_device_dmc_integration(tmp_path: Path) -> None:
    probe = probe_qspice(QSpiceSettings(workspace_root=tmp_path))
    if probe.executable is None or not probe.exists:
        pytest.skip("QSpice executable is not available for integration tests.")
    qspice_path = probe.executable
    dmc = qspice_path.parent / "dm" / "bin" / "dmc.exe"
    if not dmc.is_file():
        pytest.skip("bundled DMC not found beside the QSpice install")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "stub_device.cpp"
    source.write_text(
        "\n".join(
            [
                "#define WIN32_LEAN_AND_MEAN",
                "#include <windows.h>",
                'extern "C" __declspec(dllexport) void stub_device(void) {}',
            ]
        ),
        encoding="utf-8",
    )

    result = build_dll_device(
        source,
        workspace_root=workspace,
        toolchain="dmc",
        qspice_executable=qspice_path,
        timeout_s=180.0,
    )

    assert result.toolchain == "dmc"
    assert result.output_path.is_file()


def test_describe_dll_build_toolchain_reports_bundled_dmc(tmp_path: Path) -> None:
    qspice_exe = tmp_path / "QSPICE64.exe"
    qspice_exe.write_text("", encoding="utf-8")
    dmc = tmp_path / "dm" / "bin"
    dmc.mkdir(parents=True)
    (dmc / "dmc.exe").write_text("", encoding="utf-8")

    snapshot = describe_dll_build_toolchain(qspice_executable=qspice_exe)

    assert snapshot.dmc_available is True
    assert snapshot.auto_toolchain == "dmc"
    assert snapshot.dmc_path == (dmc / "dmc.exe").resolve(strict=False)


def test_describe_dll_build_toolchain_reports_missing_toolchains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.which",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_vcvars64_bat",
        lambda: None,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_bundled_dmc",
        lambda _exe: None,
    )

    snapshot = describe_dll_build_toolchain(qspice_executable=None)

    assert snapshot.dmc_available is False
    assert snapshot.msvc_available is False
    assert snapshot.cmake_available is False
    assert snapshot.auto_toolchain is None
    assert any("No DLL build toolchain" in note for note in snapshot.notes)


def test_auto_falls_back_to_msvc_when_dmc_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "buck_controller.cpp"
    source.write_text("// test source\n", encoding="utf-8")
    output = workspace / "buck_controller.dll"
    output.write_bytes(b"MZ")
    qspice_exe = _fake_qspice_install(tmp_path)

    monkeypatch.setattr("qspice_mcp.services.mixed_signal.build_dll_device.which", lambda _: None)
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.find_vcvars64_bat",
        lambda: tmp_path / "vcvars64.bat",
    )

    calls: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        cwd: Path,
        timeout_s: float | None,
        env: dict[str, str] | None = None,
    ) -> SubprocessResult:
        calls.append(command)
        if command[0].endswith("dmc.exe") or (len(command) >= 2 and command[1] == "-mn"):
            return SubprocessResult(
                command=command,
                working_directory=cwd,
                exit_code=1,
                duration_s=0.1,
                stdout="",
                stderr="dmc failed",
            )
        return SubprocessResult(
            command=command,
            working_directory=cwd,
            exit_code=0,
            duration_s=0.1,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal.build_dll_device.run_subprocess",
        fake_run,
    )

    result = build_dll_device(
        source,
        workspace_root=workspace,
        toolchain="auto",
        qspice_executable=qspice_exe,
    )

    assert result.toolchain == "msvc"
    assert len(calls) == 2


def test_dll_build_degradation_hints_include_recovery_suggestions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.which",
        lambda _name: None,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_vcvars64_bat",
        lambda: None,
    )
    monkeypatch.setattr(
        "qspice_mcp.services.mixed_signal._dll_toolchain_probe.find_bundled_dmc",
        lambda _exe: None,
    )

    hints = dll_build_degradation_hints(qspice_executable=None, error="no toolchain")
    assert hints["auto_toolchain"] is None
    suggestions = hints["recovery_suggestions"]
    assert isinstance(suggestions, list)
    assert any("describe_server_capabilities" in str(item) for item in suggestions)
