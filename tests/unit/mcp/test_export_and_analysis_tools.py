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
from qspice_mcp.services.simulation.list_plot_suggestions import (
    PlotSuggestion,
    PlotSuggestionCatalog,
)
from qspice_mcp.services.simulation.prepare_bode_analysis import PreparedBodeAnalysis
from qspice_mcp.services.waveform.compute_thd import ThdAnalysis, ThdHarmonic

mcp_artifact_tools = importlib.import_module("qspice_mcp.mcp.tools.artifacts")
mcp_capabilities = importlib.import_module("qspice_mcp.mcp.capabilities")
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
