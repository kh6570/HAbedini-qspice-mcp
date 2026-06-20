"""Focused MCP tests for newly added Phase 9 and Phase 10 tools."""

from __future__ import annotations

import importlib

import pytest
from mcp.shared.exceptions import McpError

from qspice_mcp.adapters.base import AdapterCapabilities, AdapterDescription
from qspice_mcp.adapters.probe import ProbeResult
from qspice_mcp.core.exceptions import BackendUnavailableError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services.artifacts._qux_export import DllVariableExport, QuxWaveformExport
from qspice_mcp.services.artifacts.describe_qux_export_support import QuxExportSupport
from qspice_mcp.services.schematic.set_component_position import ComponentPositionUpdate
from qspice_mcp.services.simulation.add_library_include import LibraryIncludeAdd
from qspice_mcp.services.simulation.add_model import ModelDefinitionAdd
from qspice_mcp.services.simulation.list_plot_suggestions import (
    PlotSuggestion,
    PlotSuggestionCatalog,
)
from qspice_mcp.services.simulation.prepare_bode_analysis import PreparedBodeAnalysis
from qspice_mcp.services.simulation.prepare_dc_sweep import PreparedDcSweep
from qspice_mcp.services.simulation.prepare_loop_gain_analysis import PreparedLoopGainAnalysis
from qspice_mcp.services.simulation.prepare_noise import PreparedNoiseAnalysis
from qspice_mcp.services.simulation.prepare_sensitivity import PreparedSensitivityAnalysis
from qspice_mcp.services.simulation.prepare_temperature_sweep import PreparedTemperatureSweep
from qspice_mcp.services.simulation.prepare_transfer_function import (
    PreparedTransferFunctionAnalysis,
)
from qspice_mcp.services.waveform.compute_thd import ThdAnalysis, ThdHarmonic
from qspice_mcp.services.waveform.measure_stability_margins import StabilityMargins
from qspice_mcp.services.waveform.measure_step_response import StepResponseMeasurement
from qspice_mcp.services.waveform.read_fourier import FourierLogInspection

mcp_artifact_tools = importlib.import_module("qspice_mcp.mcp.tools.artifacts")
mcp_capabilities = importlib.import_module("qspice_mcp.mcp.capabilities")
mcp_schematic_tools = importlib.import_module("qspice_mcp.mcp.tools.schematic")
mcp_simulation_tools = importlib.import_module("qspice_mcp.mcp.tools.simulation")
mcp_waveform_tools = importlib.import_module("qspice_mcp.mcp.tools.waveform")


@pytest.mark.anyio
async def test_mcp_tool_errors_expose_stable_error_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_describe_qux_export_support(*, settings: QSpiceSettings) -> QuxExportSupport:
        del settings
        raise BackendUnavailableError("Qux companion backend is unavailable.")

    monkeypatch.setattr(
        mcp_artifact_tools,
        "describe_qux_export_support_service",
        fake_describe_qux_export_support,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    with pytest.raises(McpError) as exc_info:
        await server.app.call_tool("describe_qux_export_support", {})

    assert exc_info.value.error.message == "Qux companion backend is unavailable."
    assert exc_info.value.error.data["error_code"] == "backend_unavailable"
    assert exc_info.value.error.data["error_type"] == "BackendUnavailableError"
    assert isinstance(exc_info.value.error.data["trace_id"], str)
    assert len(exc_info.value.error.data["trace_id"]) == 32


def test_mcp_describe_qux_export_support_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_describe_qux_export_support(*, settings: QSpiceSettings) -> QuxExportSupport:
        assert settings.workspace_root == tmp_path.resolve(strict=False)
        return QuxExportSupport(
            available=True,
            qspice_executable=executable.resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            supports_export=True,
            supports_netlist=True,
            supports_dll_variables=True,
            supported_switches=("-Export", "-Netlist", "-DLLvariables"),
            supported_export_formats=("CSV", "ASCII", "SPICE", "S2P"),
            waveform_input_suffixes=(".qraw",),
            schematic_input_suffixes=(".qsch",),
            notes=("ok",),
        )

    monkeypatch.setattr(
        mcp_artifact_tools,
        "describe_qux_export_support_service",
        fake_describe_qux_export_support,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("describe_qux_export_support")

    assert result["available"] is True
    assert result["supported_export_formats"] == ["CSV", "ASCII", "SPICE", "S2P"]


def test_mcp_describe_server_capabilities_reports_backend_state(
    monkeypatch,
    tmp_path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    probe = ProbeResult(
        configured=True,
        executable=executable.resolve(strict=False),
        exists=True,
        source="configured",
        version="2026.05",
        version_source="cli",
        note="Detected version: 2026.05 (source: cli)",
    )
    adapter = AdapterDescription(
        key="cli.v1",
        title="Current QSpice CLI",
        available=True,
        executable=executable.resolve(strict=False),
        capabilities=AdapterCapabilities(probe=True, cli_invocation=True),
    )

    class _SelectedAdapter:
        def describe(self, effective_probe: ProbeResult) -> AdapterDescription:
            assert effective_probe == probe
            return adapter

    monkeypatch.setattr(mcp_capabilities, "probe_qspice", lambda settings: probe)
    monkeypatch.setattr(mcp_capabilities, "describe_adapters", lambda effective_probe: (adapter,))
    monkeypatch.setattr(
        mcp_capabilities,
        "select_adapter",
        lambda effective_probe: _SelectedAdapter(),
    )
    monkeypatch.setattr(
        mcp_capabilities, "_load_rawread_factory", lambda: (object(), "mock_backend")
    )
    monkeypatch.setattr(mcp_capabilities, "load_rawwrite_api", lambda: (None, None, None))
    monkeypatch.setattr(
        mcp_capabilities,
        "describe_telemetry_state",
        lambda *, telemetry_enabled: {
            "enabled": telemetry_enabled,
            "dependencies_installed": True,
            "tracer_provider_configured": True,
            "tracer_provider_class": "TracerProvider",
            "span_processors": ["BatchSpanProcessor"],
            "exporters": ["ConsoleSpanExporter"],
            "exporters_configured": True,
            "spans_emitting": telemetry_enabled,
            "notes": ["Telemetry is configured."],
        },
    )
    monkeypatch.setattr(
        mcp_capabilities,
        "describe_qux_export_support",
        lambda *, settings: QuxExportSupport(
            available=False,
            qspice_executable=executable.resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            supports_export=False,
            supports_netlist=False,
            supports_dll_variables=False,
            supported_switches=("-Export", "-Netlist", "-DLLvariables"),
            supported_export_formats=("CSV", "ASCII", "SPICE", "S2P"),
            waveform_input_suffixes=(".qraw",),
            schematic_input_suffixes=(".qsch",),
            notes=("QSpice is available, but companion QUX.exe was not found next to it.",),
        ),
    )

    server = create_server(
        QSpiceSettings(
            exe=executable,
            workspace_root=tmp_path,
            telemetry_enabled=True,
        )
    )
    result = server.invoke_tool("describe_server_capabilities")

    assert result["server"]["telemetry_enabled"] is True
    assert result["telemetry"]["enabled"] is True
    assert result["telemetry"]["tracer_provider_configured"] is True
    assert result["telemetry"]["exporters"] == ["ConsoleSpanExporter"]
    assert result["telemetry"]["spans_emitting"] is True
    assert result["qspice"]["version"] == "2026.05"
    assert result["optional_backends"]["rawread"]["available"] is True
    assert result["optional_backends"]["rawread"]["backend"] == "mock_backend"
    assert result["optional_backends"]["rawwrite"]["available"] is False
    assert result["optional_backends"]["qux_companion"]["available"] is False
    assert result["feature_flags"]["native_mc_staging"] is True
    assert result["feature_flags"]["local_remote_sessions"] is True
    assert result["feature_flags"]["restart_safe_batch_rehydration"] is True
    assert result["feature_flags"]["live_gui_manifest_scaffolding"] is True
    assert result["feature_flags"]["live_gui_external_bridge_required"] is True
    assert result["feature_flags"]["clean_room_stepped_real_raw_export"] is True
    assert result["feature_flags"]["clean_room_complex_frequency_raw_export"] is True
    assert result["feature_flags"]["published_error_taxonomy"] is True
    assert result["error_taxonomy"]["document_path"] == "docs/errors.md"
    assert result["error_taxonomy"]["default_code"] == "qspice_error"
    assert any(
        code["code"] == "backend_unavailable" and code["status"] == "implemented"
        for code in result["error_taxonomy"]["codes"]
    )
    assert any(
        code["code"] == "batch_conflict" and code["status"] == "reserved"
        for code in result["error_taxonomy"]["codes"]
    )
    assert any(
        group["name"] == "companion_qux_exports" and group["state"] == "degraded"
        for group in result["degraded_groups"]
    )
    assert any(
        group["name"] == "extended_raw_export" and group["state"] == "partial"
        for group in result["degraded_groups"]
    )
    assert any(
        group["name"] == "live_gui_optional" and group["state"] == "partial"
        for group in result["degraded_groups"]
    )


def test_mcp_describe_server_capabilities_reports_partial_waveform_support_without_rawread(
    monkeypatch,
    tmp_path,
) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    probe = ProbeResult(
        configured=True,
        executable=executable.resolve(strict=False),
        exists=True,
        source="configured",
        version="2026.05",
        version_source="cli",
        note="Detected version: 2026.05 (source: cli)",
    )
    adapter = AdapterDescription(
        key="cli.v1",
        title="Current QSpice CLI",
        available=True,
        executable=executable.resolve(strict=False),
        capabilities=AdapterCapabilities(probe=True, cli_invocation=True),
    )

    class _SelectedAdapter:
        def describe(self, effective_probe: ProbeResult) -> AdapterDescription:
            assert effective_probe == probe
            return adapter

    monkeypatch.setattr(mcp_capabilities, "probe_qspice", lambda settings: probe)
    monkeypatch.setattr(mcp_capabilities, "describe_adapters", lambda effective_probe: (adapter,))
    monkeypatch.setattr(
        mcp_capabilities,
        "select_adapter",
        lambda effective_probe: _SelectedAdapter(),
    )
    monkeypatch.setattr(mcp_capabilities, "_load_rawread_factory", lambda: (None, None))
    monkeypatch.setattr(mcp_capabilities, "load_rawwrite_api", lambda: (None, None, None))
    monkeypatch.setattr(
        mcp_capabilities,
        "describe_qux_export_support",
        lambda *, settings: QuxExportSupport(
            available=False,
            qspice_executable=executable.resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            supports_export=False,
            supports_netlist=False,
            supports_dll_variables=False,
            supported_switches=("-Export", "-Netlist", "-DLLvariables"),
            supported_export_formats=("CSV", "ASCII", "SPICE", "S2P"),
            waveform_input_suffixes=(".qraw",),
            schematic_input_suffixes=(".qsch",),
            notes=("QSpice is available, but companion QUX.exe was not found next to it.",),
        ),
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("describe_server_capabilities")

    assert result["optional_backends"]["rawread"]["available"] is False
    assert (
        "common read-only waveform analysis" in (result["optional_backends"]["rawread"]["notes"][0])
    )
    assert any(
        group["name"] == "waveform_access" and group["state"] == "partial"
        for group in result["degraded_groups"]
    )


def test_mcp_export_waveform_ascii_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_export_waveform_ascii(
        raw_path: str,
        *,
        workspace_root,
        settings,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> QuxWaveformExport:
        del point_count, settings
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert expressions == ["V(out)"]
        return QuxWaveformExport(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            output_path=(tmp_path / (output_path or "out.txt")).resolve(strict=False),
            format="ASCII",
            expressions=("V(out)",),
            point_count=None,
            line_count=2,
            command=("QUX.exe", "-Export"),
        )

    monkeypatch.setattr(
        mcp_artifact_tools,
        "export_waveform_ascii_service",
        fake_export_waveform_ascii,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "export_waveform_ascii",
        raw_path="demo.qraw",
        expressions=["V(out)"],
        output_path="ascii.txt",
    )

    assert result["format"] == "ASCII"
    assert result["output_path"].endswith("ascii.txt")


def test_mcp_export_waveform_csv_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_export_waveform_csv(
        raw_path: str,
        *,
        workspace_root,
        settings,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> QuxWaveformExport:
        del point_count, settings
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert expressions == ["V(out)"]
        return QuxWaveformExport(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            output_path=(tmp_path / (output_path or "out.csv")).resolve(strict=False),
            format="CSV",
            expressions=("V(out)",),
            point_count=None,
            line_count=2,
            command=("QUX.exe", "-Export"),
        )

    monkeypatch.setattr(
        mcp_artifact_tools,
        "export_waveform_csv_service",
        fake_export_waveform_csv,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "export_waveform_csv",
        raw_path="demo.qraw",
        expressions=["V(out)"],
        output_path="trace.csv",
    )

    assert result["format"] == "CSV"
    assert result["output_path"].endswith("trace.csv")


def test_mcp_generate_dll_variables_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_generate_dll_variables(
        schematic_path: str,
        *,
        workspace_root,
        settings,
        output_path: str | None = None,
    ) -> DllVariableExport:
        del settings
        assert workspace_root == tmp_path.resolve(strict=False)
        assert schematic_path == "demo.qsch"
        return DllVariableExport(
            schematic_path=(tmp_path / schematic_path).resolve(strict=False),
            qux_path=(tmp_path / "QUX.exe").resolve(strict=False),
            output_path=(tmp_path / (output_path or "dllvars.txt")).resolve(strict=False),
            line_count=2,
            command=("QUX.exe", "-DLLvariables"),
        )

    monkeypatch.setattr(
        mcp_artifact_tools,
        "generate_dll_variables_service",
        fake_generate_dll_variables,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "generate_dll_variables",
        schematic_path="demo.qsch",
        output_path="vars.txt",
    )

    assert result["line_count"] == 2
    assert result["output_path"].endswith("vars.txt")


def test_mcp_prepare_bode_analysis_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_bode_analysis(
        source_path: str,
        *,
        workspace_root,
        perturbation_source: str,
        settling_time: str,
        start_frequency: str,
        stop_frequency: str,
        injection_amplitude: str,
        square_periods: int | None = None,
        debug: bool = False,
        skip_bias_point: bool = False,
        use_initial_conditions: bool = False,
        output_path: str | None = None,
    ) -> PreparedBodeAnalysis:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "loop.qsch"
        assert perturbation_source == "VPERT"
        assert settling_time == "5m"
        assert start_frequency == "1k"
        assert stop_frequency == "1Meg"
        assert injection_amplitude == "2m"
        assert square_periods == 10
        assert debug is True
        assert skip_bias_point is False
        assert use_initial_conditions is False
        return PreparedBodeAnalysis(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / (output_path or "loop-bode.qsch")).resolve(strict=False),
            source_kind="schematic",
            instruction=".bode VPERT 5m 1k 1Meg 2m SQUARE=10 DEBUG",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_bode_analysis_service",
        fake_prepare_bode_analysis,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_bode_analysis",
        source_path="loop.qsch",
        perturbation_source="VPERT",
        settling_time="5m",
        start_frequency="1k",
        stop_frequency="1Meg",
        injection_amplitude="2m",
        square_periods=10,
        debug=True,
        output_path="loop-bode.qsch",
    )

    assert result["instruction"].startswith(".bode")
    assert result["output_path"].endswith("loop-bode.qsch")


def test_mcp_list_plot_suggestions_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_list_plot_suggestions(
        source_path: str,
        *,
        workspace_root,
        netlist_output_path: str | None = None,
    ) -> PlotSuggestionCatalog:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "loop.net"
        assert netlist_output_path is None
        return PlotSuggestionCatalog(
            source_path=(tmp_path / source_path).resolve(strict=False),
            netlist_path=(tmp_path / source_path).resolve(strict=False),
            source_kind="netlist",
            abscissa_expression="V(in)",
            suggestions=(
                PlotSuggestion(
                    kind="plot",
                    analysis="TRAN",
                    expressions=("V(out)",),
                    directive=".plot tran V(out)",
                ),
            ),
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "list_plot_suggestions_service",
        fake_list_plot_suggestions,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("list_plot_suggestions", source_path="loop.net")

    assert result["abscissa_expression"] == "V(in)"
    assert result["suggestions"][0]["analysis"] == "TRAN"


def test_mcp_compute_thd_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_compute_thd(
        raw_path: str,
        *,
        workspace_root,
        signal: str,
        fundamental_hz: float,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: str = "auto",
        periods: int = 5,
        harmonics: int = 10,
        t_end: float | None = None,
        samples_per_cycle: int = 512,
    ) -> ThdAnalysis:
        del step, step_filters, component, periods, harmonics, t_end, samples_per_cycle
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert signal == "V(out)"
        assert fundamental_hz == 50.0
        return ThdAnalysis(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            plot_name="Transient Analysis",
            signal=signal,
            step=0,
            component="real",
            sample_count=4096,
            window_start_s=0.0,
            window_end_s=0.1,
            fundamental_hz=50.0,
            harmonics=10,
            fundamental_amplitude=1.0,
            fundamental_rms=0.70710678118,
            thd_ratio=0.1,
            thd_percent=10.0,
            contributions=(
                ThdHarmonic(
                    harmonic=1,
                    frequency_hz=50.0,
                    amplitude=1.0,
                    rms=0.70710678118,
                    percent_of_fundamental=100.0,
                ),
            ),
        )

    monkeypatch.setattr(mcp_waveform_tools, "compute_thd_service", fake_compute_thd)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "compute_thd",
        raw_path="demo.qraw",
        signal="V(out)",
        fundamental_hz=50.0,
    )

    assert result["thd_percent"] == 10.0
    assert result["contributions"][0]["harmonic"] == 1


def test_mcp_prepare_loop_gain_analysis_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_loop_gain_analysis(
        source_path: str,
        *,
        workspace_root,
        method: str,
        sweep_type: str,
        points: str,
        start: str,
        stop: str,
        expected_loop_gain_signal: str = "OpenLoopGain",
        output_path: str | None = None,
    ) -> PreparedLoopGainAnalysis:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "loop.qsch"
        assert method == "middlebrook"
        assert sweep_type == "dec"
        assert points == "100"
        assert start == "1"
        assert stop == "1Meg"
        assert expected_loop_gain_signal == "LoopGain"
        return PreparedLoopGainAnalysis(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / (output_path or "loop-loop-gain.qsch")).resolve(strict=False),
            source_kind="schematic",
            method="middlebrook",
            instruction=".ac dec 100 1 1Meg",
            reference_example="MiddleBrook.qsch",
            method_notes=("note",),
            expected_loop_gain_signal="LoopGain",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_loop_gain_analysis_service",
        fake_prepare_loop_gain_analysis,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_loop_gain_analysis",
        source_path="loop.qsch",
        method="middlebrook",
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
        expected_loop_gain_signal="LoopGain",
        output_path="loop-loop-gain.qsch",
    )

    assert result["method"] == "middlebrook"
    assert result["instruction"] == ".ac dec 100 1 1Meg"


def test_mcp_prepare_dc_sweep_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_dc_sweep(
        source_path: str,
        *,
        workspace_root,
        source: str,
        start: str,
        stop: str,
        step: str,
        output_path: str | None = None,
    ) -> PreparedDcSweep:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "divider.qsch"
        assert source == "V1"
        assert start == "0"
        assert stop == "5"
        assert step == "0.1"
        return PreparedDcSweep(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / (output_path or "divider-dc.qsch")).resolve(strict=False),
            source_kind="schematic",
            instruction=".dc V1 0 5 0.1",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_dc_sweep_service",
        fake_prepare_dc_sweep,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_dc_sweep",
        source_path="divider.qsch",
        source="V1",
        start="0",
        stop="5",
        step="0.1",
        output_path="divider-dc.qsch",
    )

    assert result["instruction"] == ".dc V1 0 5 0.1"


def test_mcp_measure_stability_margins_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_measure_stability_margins(
        raw_path: str,
        *,
        workspace_root,
        signal: str,
        step: int | None = None,
        step_filters=None,
    ) -> StabilityMargins:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "loop.qraw"
        assert signal == "OpenLoopGain"
        assert step is None
        return StabilityMargins(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            plot_name="AC Analysis",
            axis_name="Frequency",
            signal="OpenLoopGain",
            step=0,
            sample_count=100,
            gain_crossover_hz=1000.0,
            phase_margin_deg=60.0,
            phase_crossover_hz=5000.0,
            gain_margin_db=12.0,
            stable_at_unity=True,
        )

    monkeypatch.setattr(
        mcp_waveform_tools,
        "measure_stability_margins_service",
        fake_measure_stability_margins,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "measure_stability_margins",
        raw_path="loop.qraw",
        signal="OpenLoopGain",
    )

    assert result["phase_margin_deg"] == 60.0
    assert result["stable_at_unity"] is True


def test_mcp_prepare_noise_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_noise(
        source_path: str,
        *,
        workspace_root,
        output_node: str,
        input_source: str,
        sweep_type: str,
        points: str,
        start: str,
        stop: str,
        output_path: str | None = None,
    ):
        assert output_node == "V(out)"
        return PreparedNoiseAnalysis(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / "amp-noise.net").resolve(strict=False),
            source_kind="netlist",
            instruction=".noise V(out) VIN dec 100 1 1Meg",
        )

    monkeypatch.setattr(mcp_simulation_tools, "prepare_noise_service", fake_prepare_noise)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_noise",
        source_path="amp.net",
        output_node="V(out)",
        input_source="VIN",
        sweep_type="dec",
        points="100",
        start="1",
        stop="1Meg",
    )

    assert result["instruction"].startswith(".noise")


def test_mcp_prepare_temperature_sweep_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_temperature_sweep(
        source_path: str,
        *,
        workspace_root,
        start: str,
        stop: str,
        step: str,
        output_path: str | None = None,
    ):
        return PreparedTemperatureSweep(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / "amp-temp.net").resolve(strict=False),
            source_kind="netlist",
            instruction=".step temp -40 125 25",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_temperature_sweep_service",
        fake_prepare_temperature_sweep,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_temperature_sweep",
        source_path="amp.net",
        start="-40",
        stop="125",
        step="25",
    )

    assert result["instruction"] == ".step temp -40 125 25"


def test_mcp_prepare_transfer_function_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_transfer_function(
        source_path: str,
        *,
        workspace_root,
        output_node: str,
        input_source: str,
        output_path: str | None = None,
    ):
        return PreparedTransferFunctionAnalysis(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / "amp-tf.net").resolve(strict=False),
            source_kind="netlist",
            instruction=".tf V(out) VIN",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_transfer_function_service",
        fake_prepare_transfer_function,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_transfer_function",
        source_path="amp.net",
        output_node="V(out)",
        input_source="VIN",
    )

    assert result["instruction"] == ".tf V(out) VIN"


def test_mcp_prepare_sensitivity_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_sensitivity(
        source_path: str,
        *,
        workspace_root,
        analysis_type: str,
        output_node: str,
        output_path: str | None = None,
    ):
        return PreparedSensitivityAnalysis(
            source_path=(tmp_path / source_path).resolve(strict=False),
            output_path=(tmp_path / "amp-sens.net").resolve(strict=False),
            source_kind="netlist",
            instruction=".sens ac V(out)",
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_sensitivity_service",
        fake_prepare_sensitivity,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_sensitivity",
        source_path="amp.net",
        analysis_type="ac",
        output_node="V(out)",
    )

    assert result["instruction"] == ".sens ac V(out)"


def test_mcp_set_component_position_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_set_component_position(
        schematic_path: str,
        *,
        workspace_root,
        reference: str,
        position_x: int,
        position_y: int,
        rotation_degrees: int | None = None,
        output_path: str | None = None,
    ):
        return ComponentPositionUpdate(
            schematic_path=(tmp_path / schematic_path).resolve(strict=False),
            output_path=(tmp_path / "demo-moved.qsch").resolve(strict=False),
            reference=reference,
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees or 0,
        )

    monkeypatch.setattr(
        mcp_schematic_tools,
        "set_component_position_service",
        fake_set_component_position,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "set_component_position",
        schematic_path="demo.qsch",
        reference="R1",
        position_x=320,
        position_y=240,
    )

    assert result["position_x"] == 320
    assert result["position_y"] == 240


def test_mcp_measure_step_response_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_measure_step_response(
        raw_path: str,
        *,
        workspace_root,
        signal: str,
        **kwargs: object,
    ):
        del kwargs, workspace_root
        return StepResponseMeasurement(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            plot_name="Transient Analysis",
            axis_name="time",
            signal=signal,
            step=0,
            sample_count=8,
            x_unit="s",
            y_unit="V",
            initial_value=0.0,
            final_value=1.0,
            rise_time_s=1.42,
            delay_time_s=2.0,
            overshoot_pct=15.0,
            settling_time_s=5.0,
            peak_value=1.15,
        )

    monkeypatch.setattr(
        mcp_waveform_tools,
        "measure_step_response_service",
        fake_measure_step_response,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "measure_step_response",
        raw_path="step.qraw",
        signal="V(out)",
    )

    assert result["rise_time_s"] == 1.42


def test_mcp_read_fourier_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_read_fourier(log_path: str, *, workspace_root):
        del workspace_root
        return FourierLogInspection(
            log_path=(tmp_path / log_path).resolve(strict=False),
            analyses=(),
        )

    monkeypatch.setattr(mcp_waveform_tools, "read_fourier_service", fake_read_fourier)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("read_fourier", log_path="demo.log")

    assert result["analyses"] == []


def test_mcp_add_library_include_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    netlist = tmp_path / "amp.net"
    netlist.write_text("* amp\n.end\n", encoding="utf-8")
    library = tmp_path / "models.lib"
    library.write_text("* lib\n.end\n", encoding="utf-8")

    def fake_add_library_include(
        netlist_path: str,
        *,
        workspace_root,
        include_path: str,
        kind: str = "include",
        output_path: str | None = None,
        relative_to_netlist: bool = True,
    ):
        del kind, output_path, relative_to_netlist, workspace_root
        return LibraryIncludeAdd(
            source_netlist=netlist.resolve(strict=False),
            output_netlist=netlist.resolve(strict=False),
            include_path=library.resolve(strict=False),
            directive=f".include {include_path}",
            already_present=False,
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "add_library_include_service",
        fake_add_library_include,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_library_include",
        netlist_path="amp.net",
        include_path="models.lib",
    )

    assert result["directive"] == ".include models.lib"


def test_mcp_add_model_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    library = tmp_path / "devices.lib"
    library.write_text("* devices\n.end\n", encoding="utf-8")

    def fake_add_model(
        target_path: str,
        *,
        workspace_root,
        model_text: str,
        output_path: str | None = None,
    ):
        del workspace_root, model_text, output_path
        return ModelDefinitionAdd(
            source_path=library.resolve(strict=False),
            output_path=library.resolve(strict=False),
            model_name="NMOS1",
            line_count=1,
        )

    monkeypatch.setattr(mcp_simulation_tools, "add_model_service", fake_add_model)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "add_model",
        target_path="devices.lib",
        model_text=".model NMOS1 NMOS (VTO=1)",
    )

    assert result["model_name"] == "NMOS1"
