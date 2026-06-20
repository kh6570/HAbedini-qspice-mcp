"""Simulation tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.simulation.add_library_include import (
    add_library_include as add_library_include_service,
)
from qspice_mcp.services.simulation.add_model import (
    add_model as add_model_service,
)
from qspice_mcp.services.simulation.generate_netlist import (
    generate_netlist as generate_netlist_service,
)
from qspice_mcp.services.simulation.list_includes import (
    list_includes as list_includes_service,
)
from qspice_mcp.services.simulation.list_plot_suggestions import (
    list_plot_suggestions as list_plot_suggestions_service,
)
from qspice_mcp.services.simulation.prepare_ac import (
    prepare_ac as prepare_ac_service,
)
from qspice_mcp.services.simulation.prepare_bode_analysis import (
    prepare_bode_analysis as prepare_bode_analysis_service,
)
from qspice_mcp.services.simulation.prepare_dc_sweep import (
    prepare_dc_sweep as prepare_dc_sweep_service,
)
from qspice_mcp.services.simulation.prepare_loop_gain_analysis import (
    prepare_loop_gain_analysis as prepare_loop_gain_analysis_service,
)
from qspice_mcp.services.simulation.prepare_monte_carlo import (
    prepare_monte_carlo as prepare_monte_carlo_service,
)
from qspice_mcp.services.simulation.prepare_noise import (
    prepare_noise as prepare_noise_service,
)
from qspice_mcp.services.simulation.prepare_sensitivity import (
    prepare_sensitivity as prepare_sensitivity_service,
)
from qspice_mcp.services.simulation.prepare_temperature_sweep import (
    prepare_temperature_sweep as prepare_temperature_sweep_service,
)
from qspice_mcp.services.simulation.prepare_transfer_function import (
    prepare_transfer_function as prepare_transfer_function_service,
)
from qspice_mcp.services.simulation.prepare_transient import (
    prepare_transient as prepare_transient_service,
)
from qspice_mcp.services.simulation.prepare_worst_case import (
    prepare_worst_case as prepare_worst_case_service,
)
from qspice_mcp.services.simulation.resolve_model_libraries import (
    resolve_model_libraries as resolve_model_libraries_service,
)
from qspice_mcp.services.simulation.run_model_sweep import (
    run_model_sweep as run_model_sweep_service,
)
from qspice_mcp.services.simulation.run_monte_carlo import (
    run_monte_carlo as run_monte_carlo_service,
)
from qspice_mcp.services.simulation.run_param_sweep import (
    run_param_sweep as run_param_sweep_service,
)
from qspice_mcp.services.simulation.run_simulation import (
    run_simulation as run_simulation_service,
)
from qspice_mcp.services.simulation.run_value_sweep import (
    run_value_sweep as run_value_sweep_service,
)
from qspice_mcp.services.simulation.run_worst_case import (
    run_worst_case as run_worst_case_service,
)
from qspice_mcp.services.simulation.save_netlist_copy import (
    save_netlist_copy as save_netlist_copy_service,
)
from qspice_mcp.services.simulation.summarize_tolerance_analysis import (
    summarize_tolerance_analysis as summarize_tolerance_analysis_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

SIMULATION_HANDLER_NAMES = (
    "generate_netlist",
    "save_netlist_copy",
    "prepare_bode_analysis",
    "prepare_ac",
    "prepare_dc_sweep",
    "prepare_loop_gain_analysis",
    "prepare_noise",
    "prepare_sensitivity",
    "prepare_temperature_sweep",
    "prepare_transfer_function",
    "prepare_transient",
    "prepare_monte_carlo",
    "prepare_worst_case",
    "list_plot_suggestions",
    "list_includes",
    "resolve_model_libraries",
    "add_library_include",
    "add_model",
    "run_simulation",
    "run_value_sweep",
    "run_param_sweep",
    "run_monte_carlo",
    "run_worst_case",
    "run_model_sweep",
    "summarize_tolerance_analysis",
)


class SimulationToolMixin:
    """Handlers for simulation planning and execution tools."""

    def generate_netlist(
        self: _RuntimeWithSettings, source_path: str, output_path: str | None = None
    ) -> dict[str, object]:
        generated = generate_netlist_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
            settings=self.settings,
        )
        return to_json_object(generated)

    def save_netlist_copy(
        self: _RuntimeWithSettings,
        source_path: str,
        output_path: str,
    ) -> dict[str, object]:
        saved = save_netlist_copy_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
        )
        return to_json_object(saved)

    def prepare_bode_analysis(
        self: _RuntimeWithSettings,
        source_path: str,
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
    ) -> dict[str, object]:
        prepared = prepare_bode_analysis_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            perturbation_source=perturbation_source,
            settling_time=settling_time,
            start_frequency=start_frequency,
            stop_frequency=stop_frequency,
            injection_amplitude=injection_amplitude,
            square_periods=square_periods,
            debug=debug,
            skip_bias_point=skip_bias_point,
            use_initial_conditions=use_initial_conditions,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_ac(
        self: _RuntimeWithSettings,
        source_path: str,
        sweep_type: str,
        points: str,
        start: str,
        stop: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_ac_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            sweep_type=sweep_type,
            points=points,
            start=start,
            stop=stop,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_dc_sweep(
        self: _RuntimeWithSettings,
        source_path: str,
        source: str,
        start: str,
        stop: str,
        step: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_dc_sweep_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            source=source,
            start=start,
            stop=stop,
            step=step,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_loop_gain_analysis(
        self: _RuntimeWithSettings,
        source_path: str,
        method: Literal["tian", "middlebrook"],
        sweep_type: str,
        points: str,
        start: str,
        stop: str,
        expected_loop_gain_signal: str = "OpenLoopGain",
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_loop_gain_analysis_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            method=method,
            sweep_type=sweep_type,
            points=points,
            start=start,
            stop=stop,
            expected_loop_gain_signal=expected_loop_gain_signal,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_noise(
        self: _RuntimeWithSettings,
        source_path: str,
        output_node: str,
        input_source: str,
        sweep_type: str,
        points: str,
        start: str,
        stop: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_noise_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            output_node=output_node,
            input_source=input_source,
            sweep_type=sweep_type,
            points=points,
            start=start,
            stop=stop,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_transfer_function(
        self: _RuntimeWithSettings,
        source_path: str,
        output_node: str,
        input_source: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_transfer_function_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            output_node=output_node,
            input_source=input_source,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_sensitivity(
        self: _RuntimeWithSettings,
        source_path: str,
        analysis_type: str,
        output_node: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_sensitivity_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            analysis_type=analysis_type,
            output_node=output_node,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_temperature_sweep(
        self: _RuntimeWithSettings,
        source_path: str,
        start: str,
        stop: str,
        step: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_temperature_sweep_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            start=start,
            stop=stop,
            step=step,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_transient(
        self: _RuntimeWithSettings,
        source_path: str,
        step: str,
        stop: str,
        start: str | None = None,
        max_step: str | None = None,
        use_initial_conditions: bool = False,
        skip_bias_point: bool = False,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_transient_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            step=step,
            stop=stop,
            start=start,
            max_step=max_step,
            use_initial_conditions=use_initial_conditions,
            skip_bias_point=skip_bias_point,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_monte_carlo(
        self: _RuntimeWithSettings,
        source_path: str,
        sample_count: int,
        parameters: dict[str, dict[str, int | float]] | None = None,
        component_values: dict[str, dict[str, int | float]] | None = None,
        component_presets: dict[str, dict[str, int | float]] | None = None,
        seed: int = 0,
        stage_native_mc: bool = False,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_monte_carlo_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            parameters=parameters,
            component_values=component_values,
            component_presets=component_presets,
            sample_count=sample_count,
            seed=seed,
            stage_native_mc=stage_native_mc,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def prepare_worst_case(
        self: _RuntimeWithSettings,
        source_path: str,
        parameters: dict[str, dict[str, int | float]] | None = None,
        component_values: dict[str, dict[str, int | float]] | None = None,
        component_presets: dict[str, dict[str, int | float]] | None = None,
        mode: Literal["corners", "one_at_a_time"] = "corners",
        include_nominal: bool = True,
        output_path: str | None = None,
    ) -> dict[str, object]:
        prepared = prepare_worst_case_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            parameters=parameters,
            component_values=component_values,
            component_presets=component_presets,
            mode=mode,
            include_nominal=include_nominal,
            output_path=output_path,
        )
        return to_json_object(prepared)

    def list_plot_suggestions(
        self: _RuntimeWithSettings,
        source_path: str,
        netlist_output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = list_plot_suggestions_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            netlist_output_path=netlist_output_path,
        )
        return to_json_object(inspection)

    def list_includes(
        self: _RuntimeWithSettings,
        netlist_path: str,
    ) -> dict[str, object]:
        inspection = list_includes_service(
            netlist_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(inspection)

    def resolve_model_libraries(
        self: _RuntimeWithSettings,
        netlist_path: str,
    ) -> dict[str, object]:
        inspection = resolve_model_libraries_service(
            netlist_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(inspection)

    def add_library_include(
        self: _RuntimeWithSettings,
        netlist_path: str,
        include_path: str,
        kind: Literal["include", "inc", "lib"] = "include",
        output_path: str | None = None,
        relative_to_netlist: bool = True,
    ) -> dict[str, object]:
        result = add_library_include_service(
            netlist_path,
            workspace_root=self.settings.workspace_root,
            include_path=include_path,
            kind=kind,
            output_path=output_path,
            relative_to_netlist=relative_to_netlist,
        )
        return to_json_object(result)

    def add_model(
        self: _RuntimeWithSettings,
        target_path: str,
        model_text: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        result = add_model_service(
            target_path,
            workspace_root=self.settings.workspace_root,
            model_text=model_text,
            output_path=output_path,
        )
        return to_json_object(result)

    def run_simulation(
        self: _RuntimeWithSettings,
        source_path: str,
        dry_run: bool = False,
        timeout_s: float | None = None,
        log_path: str | None = None,
        raw_output_path: str | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        netlist_output_path: str | None = None,
    ) -> dict[str, object]:
        resolved_source = resolve_workspace_path(
            source_path, workspace_root=self.settings.workspace_root
        )
        generated_netlist: dict[str, object] | None = None
        warnings: list[str] = []
        simulation_input = resolved_source

        if resolved_source.suffix.lower() == ".qsch":
            generated = generate_netlist_service(
                resolved_source,
                workspace_root=self.settings.workspace_root,
                output_path=netlist_output_path,
                settings=self.settings,
            )
            generated_netlist = to_json_object(generated)
            warnings.extend(str(item) for item in generated.warnings)
            simulation_input = generated.netlist_path
        elif netlist_output_path is not None:
            warnings.append(
                "netlist_output_path is ignored when source_path already points "
                "to a .net or .cir file."
            )

        result = run_simulation_service(
            simulation_input,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            dry_run=dry_run,
            timeout_s=timeout_s,
            log_path=log_path,
            raw_output_path=raw_output_path,
            extra_switches=tuple(extra_switches or ()),
            ascii_raw=ascii_raw,
        )
        payload = to_json_object(result)
        payload["source_path"] = str(resolved_source)
        if generated_netlist is not None:
            payload["generated_netlist"] = generated_netlist
        if warnings:
            payload["warnings"] = warnings
        return payload

    def run_value_sweep(
        self: _RuntimeWithSettings,
        source_path: str,
        reference: str,
        values: list[str | int | float],
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        inspection = run_value_sweep_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            values=values,
            settings=self.settings,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(inspection)

    def run_param_sweep(
        self: _RuntimeWithSettings,
        source_path: str,
        parameters: dict[
            str, list[str | int | float | bool] | tuple[str | int | float | bool, ...]
        ],
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        inspection = run_param_sweep_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            parameters=parameters,
            settings=self.settings,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(inspection)

    def run_model_sweep(
        self: _RuntimeWithSettings,
        source_path: str,
        reference: str,
        models: list[str],
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        inspection = run_model_sweep_service(
            source_path,
            workspace_root=self.settings.workspace_root,
            reference=reference,
            models=models,
            settings=self.settings,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(inspection)

    def run_monte_carlo(
        self: _RuntimeWithSettings,
        prepared_path: str,
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        inspection = run_monte_carlo_service(
            prepared_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(inspection)

    def run_worst_case(
        self: _RuntimeWithSettings,
        prepared_path: str,
        output_dir: str | None = None,
        parallelism: int = 1,
        dry_run: bool = False,
        timeout_s: float | None = None,
        ascii_raw: bool = False,
        extra_switches: list[str] | None = None,
        resume: bool = False,
        retained_artifact_policy: Literal[
            "cleanup", "keep_orphans", "keep_stale", "keep_all"
        ] = "cleanup",
    ) -> dict[str, object]:
        inspection = run_worst_case_service(
            prepared_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_dir=output_dir,
            parallelism=parallelism,
            dry_run=dry_run,
            timeout_s=timeout_s,
            ascii_raw=ascii_raw,
            extra_switches=tuple(extra_switches or ()),
            resume=resume,
            retained_artifact_policy=retained_artifact_policy,
        )
        return to_json_object(inspection)

    def summarize_tolerance_analysis(
        self: _RuntimeWithSettings,
        batch_path: str,
        measures: list[str] | None = None,
        refresh_measures: bool = True,
    ) -> dict[str, object]:
        inspection = summarize_tolerance_analysis_service(
            batch_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            measures=measures,
            refresh_measures=refresh_measures,
        )
        return to_json_object(inspection)


__all__ = [
    "SIMULATION_HANDLER_NAMES",
    "SimulationToolMixin",
    "generate_netlist_service",
    "list_plot_suggestions_service",
    "prepare_bode_analysis_service",
    "prepare_monte_carlo_service",
    "prepare_worst_case_service",
    "run_model_sweep_service",
    "run_monte_carlo_service",
    "run_param_sweep_service",
    "run_simulation_service",
    "run_value_sweep_service",
    "run_worst_case_service",
    "summarize_tolerance_analysis_service",
]
