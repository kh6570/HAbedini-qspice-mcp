"""Focused MCP tests for the initial Phase 7 Monte Carlo tools."""

from __future__ import annotations

import importlib

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services._internals.simulation_batch import SimulationBatch, SimulationBatchRun
from qspice_mcp.services.simulation.prepare_monte_carlo import (
    MonteCarloComponentValue,
    MonteCarloParameter,
    MonteCarloSample,
    NativeMonteCarloStage,
    PreparedMonteCarlo,
)
from qspice_mcp.services.simulation.prepare_worst_case import (
    PreparedWorstCase,
    WorstCaseCase,
    WorstCaseComponentValue,
    WorstCaseParameter,
)
from qspice_mcp.services.simulation.summarize_tolerance_analysis import (
    ToleranceAnalysisSummary,
    ToleranceComponentValueSummary,
    ToleranceMeasureSummary,
    ToleranceParameterSummary,
)

mcp_simulation_tools = importlib.import_module("qspice_mcp.mcp.tools.simulation")


def test_mcp_prepare_monte_carlo_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_monte_carlo(
        source_path: str,
        *,
        workspace_root,
        parameters: dict[str, dict[str, int | float]] | None = None,
        component_values: dict[str, dict[str, int | float]] | None = None,
        component_presets: dict[str, dict[str, int | float]] | None = None,
        sample_count: int,
        seed: int = 0,
        stage_native_mc: bool = False,
        output_path: str | None = None,
    ) -> PreparedMonteCarlo:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "demo.qsch"
        assert parameters == {"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}}
        assert component_values == {"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}}
        assert component_presets == {"R": {"tolerance_pct": 5.0}}
        assert sample_count == 4
        assert seed == 99
        assert stage_native_mc is True
        return PreparedMonteCarlo(
            source_path=(tmp_path / source_path).resolve(strict=False),
            plan_path=(tmp_path / (output_path or "plan.json")).resolve(strict=False),
            output_root=tmp_path.resolve(strict=False),
            sample_count=sample_count,
            seed=seed,
            distribution="uniform",
            parameters=(
                MonteCarloParameter(
                    name="VIN",
                    nominal=12.0,
                    tolerance_pct=5.0,
                    minimum=11.4,
                    maximum=12.6,
                ),
            ),
            component_values=(
                MonteCarloComponentValue(
                    reference="R1",
                    nominal=1000.0,
                    tolerance_pct=None,
                    minimum=900.0,
                    maximum=1100.0,
                ),
            ),
            native_mc_stage=NativeMonteCarloStage(
                schematic_path=(tmp_path / "native-mc" / "demo.qsch").resolve(strict=False),
                parameter_expressions={"VIN": "mc(12, 0.05)"},
                component_value_expressions={"R1": "mc(1000, 0.01)"},
            ),
            samples=(
                MonteCarloSample(
                    index=0,
                    parameter_values={"VIN": 12.1},
                    component_values={"R1": 980.0},
                    label="sample-000",
                ),
                MonteCarloSample(
                    index=1,
                    parameter_values={"VIN": 11.9},
                    component_values={"R1": 1020.0},
                    label="sample-001",
                ),
            ),
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_monte_carlo_service",
        fake_prepare_monte_carlo,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_monte_carlo",
        source_path="demo.qsch",
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        component_presets={"R": {"tolerance_pct": 5.0}},
        sample_count=4,
        seed=99,
        stage_native_mc=True,
        output_path="mc-plan.json",
    )

    assert result["sample_count"] == 4
    assert result["distribution"] == "uniform"
    assert result["native_mc_stage"]["parameter_expressions"]["VIN"] == "mc(12, 0.05)"


def test_mcp_run_monte_carlo_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_run_monte_carlo(
        prepared_path: str,
        *,
        workspace_root,
        settings,
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: tuple[str, ...] = (),
        resume: bool = False,
        retained_artifact_policy: str = "cleanup",
        batch_id: str | None = None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del settings, timeout_s, ascii_raw, extra_switches, batch_id, should_cancel, on_run_complete
        assert workspace_root == tmp_path.resolve(strict=False)
        assert prepared_path == "mc-plan.json"
        assert output_dir is None
        assert parallelism == 2
        assert dry_run is True
        assert resume is True
        assert retained_artifact_policy == "keep_stale"
        return SimulationBatch(
            source_path=(tmp_path / "demo.qsch").resolve(strict=False),
            output_root=(tmp_path / "artifacts" / "mc").resolve(strict=False),
            sweep_kind="monte_carlo",
            run_count=1,
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="sample-000",
                    assignment={"VIN": 12.0},
                    schematic_path=(tmp_path / "artifacts" / "mc" / "demo.qsch").resolve(
                        strict=False
                    ),
                    netlist_path=(tmp_path / "artifacts" / "mc" / "demo.net").resolve(strict=False),
                    log_path=(tmp_path / "artifacts" / "mc" / "demo.log").resolve(strict=False),
                    raw_path=(tmp_path / "artifacts" / "mc" / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=True,
                ),
            ),
            parameter_names=("VIN",),
            plan_path=(tmp_path / prepared_path).resolve(strict=False),
            seed=99,
        )

    monkeypatch.setattr(mcp_simulation_tools, "run_monte_carlo_service", fake_run_monte_carlo)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "run_monte_carlo",
        prepared_path="mc-plan.json",
        parallelism=2,
        dry_run=True,
        resume=True,
        retained_artifact_policy="keep_stale",
    )

    assert result["sweep_kind"] == "monte_carlo"
    assert result["plan_path"].endswith("mc-plan.json")


def test_mcp_prepare_worst_case_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_prepare_worst_case(
        source_path: str,
        *,
        workspace_root,
        parameters: dict[str, dict[str, int | float]] | None = None,
        component_values: dict[str, dict[str, int | float]] | None = None,
        component_presets: dict[str, dict[str, int | float]] | None = None,
        mode: str = "corners",
        include_nominal: bool = True,
        output_path: str | None = None,
    ) -> PreparedWorstCase:
        assert workspace_root == tmp_path.resolve(strict=False)
        assert source_path == "demo.qsch"
        assert parameters == {"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}}
        assert component_values == {"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}}
        assert component_presets == {"R": {"tolerance_pct": 5.0}}
        assert mode == "one_at_a_time"
        assert include_nominal is False
        return PreparedWorstCase(
            source_path=(tmp_path / source_path).resolve(strict=False),
            plan_path=(tmp_path / (output_path or "worst-case.json")).resolve(strict=False),
            output_root=(tmp_path / "artifacts" / "wc").resolve(strict=False),
            mode="one_at_a_time",
            include_nominal=False,
            parameters=(
                WorstCaseParameter(
                    name="VIN",
                    nominal=12.0,
                    tolerance_pct=5.0,
                    minimum=11.4,
                    maximum=12.6,
                ),
            ),
            cases=(
                WorstCaseCase(
                    index=0,
                    parameter_values={"VIN": 11.4},
                    component_values={"R1": 1000.0},
                    label="VIN-min",
                ),
            ),
            component_values=(
                WorstCaseComponentValue(
                    reference="R1",
                    nominal=1000.0,
                    tolerance_pct=None,
                    minimum=900.0,
                    maximum=1100.0,
                ),
            ),
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "prepare_worst_case_service",
        fake_prepare_worst_case,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "prepare_worst_case",
        source_path="demo.qsch",
        parameters={"VIN": {"nominal": 12.0, "tolerance_pct": 5.0}},
        component_values={"R1": {"nominal": 1000.0, "minimum": 900.0, "maximum": 1100.0}},
        component_presets={"R": {"tolerance_pct": 5.0}},
        mode="one_at_a_time",
        include_nominal=False,
        output_path="worst-case.json",
    )

    assert result["mode"] == "one_at_a_time"
    assert result["cases"][0]["label"] == "VIN-min"


def test_mcp_run_worst_case_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_run_worst_case(
        prepared_path: str,
        *,
        workspace_root,
        settings,
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: tuple[str, ...] = (),
        resume: bool = False,
        retained_artifact_policy: str = "cleanup",
        batch_id: str | None = None,
        should_cancel=None,
        on_run_complete=None,
    ) -> SimulationBatch:
        del settings, timeout_s, ascii_raw, extra_switches, batch_id, should_cancel, on_run_complete
        assert workspace_root == tmp_path.resolve(strict=False)
        assert prepared_path == "worst-case.json"
        assert parallelism == 2
        assert dry_run is True
        assert resume is True
        assert retained_artifact_policy == "keep_orphans"
        return SimulationBatch(
            source_path=(tmp_path / "demo.qsch").resolve(strict=False),
            output_root=(tmp_path / "artifacts" / "wc").resolve(strict=False),
            sweep_kind="worst_case",
            run_count=1,
            parallelism=2,
            sequential=False,
            runs=(
                SimulationBatchRun(
                    index=0,
                    label="VIN-min",
                    assignment={
                        "parameters": {"VIN": 11.4},
                        "component_values": {"R1": 1000.0},
                    },
                    schematic_path=(tmp_path / "artifacts" / "wc" / "demo.qsch").resolve(
                        strict=False
                    ),
                    netlist_path=(tmp_path / "artifacts" / "wc" / "demo.net").resolve(strict=False),
                    log_path=(tmp_path / "artifacts" / "wc" / "demo.log").resolve(strict=False),
                    raw_path=(tmp_path / "artifacts" / "wc" / "demo.qraw").resolve(strict=False),
                    command=("QSPICE64.exe", "demo.net"),
                    dry_run=True,
                ),
            ),
            parameter_names=("VIN",),
            plan_path=(tmp_path / prepared_path).resolve(strict=False),
        )

    monkeypatch.setattr(mcp_simulation_tools, "run_worst_case_service", fake_run_worst_case)

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "run_worst_case",
        prepared_path="worst-case.json",
        parallelism=2,
        dry_run=True,
        resume=True,
        retained_artifact_policy="keep_orphans",
    )

    assert result["sweep_kind"] == "worst_case"
    assert result["plan_path"].endswith("worst-case.json")


def test_mcp_summarize_tolerance_analysis_is_invokable(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    def fake_summarize_tolerance_analysis(
        batch_path: str,
        *,
        workspace_root,
        settings,
        measures: list[str] | None = None,
        refresh_measures: bool = True,
    ) -> ToleranceAnalysisSummary:
        del settings
        assert workspace_root == tmp_path.resolve(strict=False)
        assert batch_path == "batch.json"
        assert measures == ["vout_avg"]
        assert refresh_measures is True
        return ToleranceAnalysisSummary(
            batch_path=(tmp_path / batch_path).resolve(strict=False),
            plan_path=(tmp_path / "mc-plan.json").resolve(strict=False),
            source_path=(tmp_path / "demo.qsch").resolve(strict=False),
            output_root=(tmp_path / "artifacts" / "mc").resolve(strict=False),
            sweep_kind="monte_carlo",
            seed=42,
            status="completed",
            run_count=4,
            completed_run_count=4,
            successful_run_count=4,
            failed_run_count=0,
            parameter_summaries=(
                ToleranceParameterSummary(
                    name="VIN",
                    nominal=12.0,
                    tolerance_pct=5.0,
                    minimum=11.4,
                    maximum=12.6,
                    sample_count=4,
                    sampled_min=11.5,
                    sampled_max=12.5,
                    mean=12.0,
                    stdev=0.25,
                ),
            ),
            component_value_summaries=(
                ToleranceComponentValueSummary(
                    reference="R1",
                    nominal=1000.0,
                    tolerance_pct=None,
                    minimum=900.0,
                    maximum=1100.0,
                    sample_count=4,
                    sampled_min=940.0,
                    sampled_max=1080.0,
                    mean=1000.0,
                    stdev=40.0,
                ),
            ),
            measure_summaries=(
                ToleranceMeasureSummary(
                    name="vout_avg",
                    analysis="tran",
                    expression="avg(V(out))",
                    column="value",
                    sample_count=4,
                    minimum=4.9,
                    maximum=5.1,
                    mean=5.0,
                    stdev=0.08,
                ),
            ),
        )

    monkeypatch.setattr(
        mcp_simulation_tools,
        "summarize_tolerance_analysis_service",
        fake_summarize_tolerance_analysis,
    )

    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))
    result = server.invoke_tool(
        "summarize_tolerance_analysis",
        batch_path="batch.json",
        measures=["vout_avg"],
    )

    assert result["successful_run_count"] == 4
    assert result["component_value_summaries"][0]["reference"] == "R1"
    assert result["measure_summaries"][0]["name"] == "vout_avg"
