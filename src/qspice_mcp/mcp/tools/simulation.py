"""Simulation tool handlers."""

from __future__ import annotations

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

__all__ = [
    "add_library_include_service",
    "add_model_service",
    "generate_netlist_service",
    "list_includes_service",
    "list_plot_suggestions_service",
    "prepare_ac_service",
    "prepare_bode_analysis_service",
    "prepare_dc_sweep_service",
    "prepare_loop_gain_analysis_service",
    "prepare_monte_carlo_service",
    "prepare_noise_service",
    "prepare_sensitivity_service",
    "prepare_temperature_sweep_service",
    "prepare_transfer_function_service",
    "prepare_transient_service",
    "prepare_worst_case_service",
    "resolve_model_libraries_service",
    "run_model_sweep_service",
    "run_monte_carlo_service",
    "run_param_sweep_service",
    "run_simulation_service",
    "run_value_sweep_service",
    "run_worst_case_service",
    "save_netlist_copy_service",
    "summarize_tolerance_analysis_service",
]
