"""Focused MCP tests for Phase 6 operating-point tools."""

from __future__ import annotations

import importlib

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services.waveform.filter_device_operating_points import (
    DeviceOperatingPointFilters,
    FilteredDeviceOperatingPointCatalog,
)
from qspice_mcp.services.waveform.read_device_operating_points import (
    DeviceOperatingPoint,
    DeviceOperatingPointCatalog,
    NodeVoltage,
    OperatingPointGroup,
    OperatingPointMetric,
)
from qspice_mcp.services.waveform.summarize_device_operating_points import (
    DeviceOperatingPointExtremum,
    DeviceOperatingPointSummary,
    OperatingPointFamilySummary,
)

mcp_waveform_tools = importlib.import_module("qspice_mcp.mcp.tools.waveform")


def _demo_device(reference: str) -> DeviceOperatingPoint:
    return DeviceOperatingPoint(
        reference=reference,
        family="mosfet",
        model="NMOS",
        model_type="nmos",
        nodes=("out", "in", "0", "0"),
        metrics=(
            OperatingPointMetric(
                name="drain_current",
                trace_name=f"Id({reference})",
                value=0.01,
                unit="A",
            ),
            OperatingPointMetric(
                name="power",
                trace_name=f"P({reference})",
                value=0.02,
                unit="W",
            ),
        ),
    )


def test_mcp_read_device_operating_points_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_read_device_operating_points(
        raw_path: str,
        *,
        workspace_root,
        netlist_path: str | None = None,
    ) -> DeviceOperatingPointCatalog:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert netlist_path == "demo.net"
        return DeviceOperatingPointCatalog(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            netlist_path=(tmp_path / netlist_path).resolve(strict=False),
            plot_name="Operating Point",
            device_count=1,
            node_count=1,
            groups=(
                OperatingPointGroup(
                    family="mosfet",
                    model="NMOS",
                    device_count=1,
                    references=("M1",),
                ),
            ),
            devices=(_demo_device("M1"),),
            node_voltages=(NodeVoltage(node="out", voltage_v=0.7, trace_name="V(out)"),),
        )

    monkeypatch.setattr(
        mcp_waveform_tools,
        "read_device_operating_points_service",
        fake_read_device_operating_points,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "read_device_operating_points",
        raw_path="demo.qraw",
        netlist_path="demo.net",
    )

    assert result["plot_name"] == "Operating Point"
    assert result["devices"][0]["reference"] == "M1"


def test_mcp_filter_device_operating_points_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_filter_device_operating_points(
        raw_path: str,
        *,
        workspace_root,
        netlist_path: str | None = None,
        families: list[str] | None = None,
        models: list[str] | None = None,
        references: list[str] | None = None,
        reference_pattern: str | None = None,
        metric_names: list[str] | None = None,
    ) -> FilteredDeviceOperatingPointCatalog:
        del models, references, reference_pattern
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert netlist_path is None
        assert families == ["mosfet"]
        assert metric_names == ["power"]
        return FilteredDeviceOperatingPointCatalog(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            netlist_path=None,
            plot_name="Operating Point",
            original_device_count=2,
            device_count=1,
            node_count=1,
            groups=(
                OperatingPointGroup(
                    family="mosfet",
                    model="NMOS",
                    device_count=1,
                    references=("M1",),
                ),
            ),
            devices=(_demo_device("M1"),),
            node_voltages=(NodeVoltage(node="out", voltage_v=0.7, trace_name="V(out)"),),
            applied_filters=DeviceOperatingPointFilters(
                families=("mosfet",),
                metric_names=("power",),
            ),
        )

    monkeypatch.setattr(
        mcp_waveform_tools,
        "filter_device_operating_points_service",
        fake_filter_device_operating_points,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "filter_device_operating_points",
        raw_path="demo.qraw",
        families=["mosfet"],
        metric_names=["power"],
    )

    assert result["device_count"] == 1
    assert result["applied_filters"]["families"] == ["mosfet"]


def test_mcp_summarize_device_operating_points_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_summarize_device_operating_points(
        raw_path: str,
        *,
        workspace_root,
        netlist_path: str | None = None,
    ) -> DeviceOperatingPointSummary:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert raw_path == "demo.qraw"
        assert netlist_path is None
        return DeviceOperatingPointSummary(
            raw_path=(tmp_path / raw_path).resolve(strict=False),
            netlist_path=None,
            plot_name="Operating Point",
            device_count=1,
            node_count=1,
            family_summaries=(
                OperatingPointFamilySummary(
                    family="mosfet",
                    device_count=1,
                    models=("NMOS",),
                    total_power_w=0.02,
                ),
            ),
            highest_dissipation=DeviceOperatingPointExtremum(
                reference="M1",
                family="mosfet",
                model="NMOS",
                metric_name="power",
                trace_name="P(M1)",
                value=0.02,
                unit="W",
            ),
            lowest_dissipation=None,
            largest_abs_current=None,
            highest_node_voltage=NodeVoltage(node="out", voltage_v=0.7, trace_name="V(out)"),
            lowest_node_voltage=NodeVoltage(node="out", voltage_v=0.7, trace_name="V(out)"),
        )

    monkeypatch.setattr(
        mcp_waveform_tools,
        "summarize_device_operating_points_service",
        fake_summarize_device_operating_points,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool("summarize_device_operating_points", raw_path="demo.qraw")

    assert result["family_summaries"][0]["family"] == "mosfet"
    assert result["highest_dissipation"]["reference"] == "M1"
