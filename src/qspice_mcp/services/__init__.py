"""Application service catalog for qspice-mcp."""

from __future__ import annotations

import sys
from importlib import import_module

from ._internals.service_catalog import build_service_spec_catalog, discover_package_service_specs
from ._internals.simulation_batch import SimulationBatch, SimulationBatchRun
from ._shared.paths import resolve_workspace_path, validate_existing_file, validate_time_window
from .artifacts.compare_waveforms import SERVICE_SPEC as COMPARE_WAVEFORMS_SERVICE
from .artifacts.compare_waveforms import (
    WaveformComparison,
    WaveformComparisonRun,
    compare_waveforms,
)
from .artifacts.describe_qux_export_support import (
    SERVICE_SPEC as DESCRIBE_QUX_EXPORT_SUPPORT_SERVICE,
)
from .artifacts.describe_qux_export_support import (
    QuxExportSupport,
    describe_qux_export_support,
)
from .artifacts.export_derived_raw import SERVICE_SPEC as EXPORT_DERIVED_RAW_SERVICE
from .artifacts.export_derived_raw import DerivedRawExport, export_derived_raw
from .artifacts.export_measures_csv import SERVICE_SPEC as EXPORT_MEASURES_CSV_SERVICE
from .artifacts.export_measures_csv import MeasureCsvExport, export_measures_csv
from .artifacts.export_touchstone_s2p import SERVICE_SPEC as EXPORT_TOUCHSTONE_S2P_SERVICE
from .artifacts.export_touchstone_s2p import export_touchstone_s2p
from .artifacts.export_waveform_ascii import SERVICE_SPEC as EXPORT_WAVEFORM_ASCII_SERVICE
from .artifacts.export_waveform_ascii import QuxWaveformExport, export_waveform_ascii
from .artifacts.export_waveform_csv import SERVICE_SPEC as EXPORT_WAVEFORM_CSV_SERVICE
from .artifacts.export_waveform_csv import export_waveform_csv
from .artifacts.export_waveform_spice import SERVICE_SPEC as EXPORT_WAVEFORM_SPICE_SERVICE
from .artifacts.export_waveform_spice import export_waveform_spice
from .artifacts.generate_dll_variables import SERVICE_SPEC as GENERATE_DLL_VARIABLES_SERVICE
from .artifacts.generate_dll_variables import DllVariableExport, generate_dll_variables
from .artifacts.merge_waveforms import SERVICE_SPEC as MERGE_WAVEFORMS_SERVICE
from .artifacts.merge_waveforms import MergedWaveformExport, WaveformMergeInput, merge_waveforms
from .artifacts.summarize_batch import SERVICE_SPEC as SUMMARIZE_BATCH_SERVICE
from .artifacts.summarize_batch import BatchRunSummary, BatchSummary, summarize_batch
from .batch.cancel_batch import SERVICE_SPEC as CANCEL_BATCH_SERVICE
from .batch.cancel_batch import BatchCancellation
from .batch.collect_batch_results import SERVICE_SPEC as COLLECT_BATCH_RESULTS_SERVICE
from .batch.collect_batch_results import BatchCollection
from .batch.get_batch_status import SERVICE_SPEC as GET_BATCH_STATUS_SERVICE
from .batch.get_batch_status import BatchStatus
from .batch.submit_batch import SERVICE_SPEC as SUBMIT_BATCH_SERVICE
from .batch.submit_batch import BatchSubmission
from .instructions.list_workflow_instructions import (
    SERVICE_SPEC as LIST_WORKFLOW_INSTRUCTIONS_SERVICE,
)
from .instructions.list_workflow_instructions import (
    WorkflowInstructionList,
    list_workflow_instructions,
)
from .instructions.read_workflow_instruction import (
    SERVICE_SPEC as READ_WORKFLOW_INSTRUCTION_SERVICE,
)
from .instructions.read_workflow_instruction import (
    WorkflowInstructionDocument,
    read_workflow_instruction,
)
from .live_gui.close_live_gui_session import SERVICE_SPEC as CLOSE_LIVE_GUI_SESSION_SERVICE
from .live_gui.close_live_gui_session import LiveGuiSessionClosure
from .live_gui.describe_live_gui_support import SERVICE_SPEC as DESCRIBE_LIVE_GUI_SUPPORT_SERVICE
from .live_gui.describe_live_gui_support import LiveGuiSupport, describe_live_gui_support
from .live_gui.launch_live_gui_session import SERVICE_SPEC as LAUNCH_LIVE_GUI_SESSION_SERVICE
from .live_gui.launch_live_gui_session import LiveGuiSessionLaunch
from .live_gui.open_schematic_in_gui import SERVICE_SPEC as OPEN_SCHEMATIC_IN_GUI_SERVICE
from .live_gui.open_schematic_in_gui import OpenedSchematicInGui, open_schematic_in_gui
from .live_gui.poll_live_gui_session import SERVICE_SPEC as POLL_LIVE_GUI_SESSION_SERVICE
from .live_gui.poll_live_gui_session import LiveGuiSessionStatus
from .live_gui.poll_live_gui_session_events import (
    SERVICE_SPEC as POLL_LIVE_GUI_SESSION_EVENTS_SERVICE,
)
from .live_gui.poll_live_gui_session_events import LiveGuiSessionEvent, LiveGuiSessionEventPoll
from .live_gui.refresh_schematic_in_gui import SERVICE_SPEC as REFRESH_SCHEMATIC_IN_GUI_SERVICE
from .live_gui.refresh_schematic_in_gui import RefreshedSchematicInGui, refresh_schematic_in_gui
from .live_gui.scaffold_live_gui_session import (
    SERVICE_SPEC as SCAFFOLD_LIVE_GUI_SESSION_SERVICE,
)
from .live_gui.scaffold_live_gui_session import (
    LiveGuiSessionScaffold,
    scaffold_live_gui_session,
)
from .live_gui.send_live_gui_session_command import (
    SERVICE_SPEC as SEND_LIVE_GUI_SESSION_COMMAND_SERVICE,
)
from .live_gui.send_live_gui_session_command import LiveGuiSessionCommandDispatch
from .mixed_signal.build_dll_device import SERVICE_SPEC as BUILD_DLL_DEVICE_SERVICE
from .mixed_signal.build_dll_device import BuiltDllDevice, build_dll_device
from .mixed_signal.describe_mixed_signal_support import (
    SERVICE_SPEC as DESCRIBE_MIXED_SIGNAL_SUPPORT_SERVICE,
)
from .mixed_signal.describe_mixed_signal_support import (
    MixedSignalSupport,
    describe_mixed_signal_support,
)
from .mixed_signal.scaffold_dll_device import (
    SERVICE_SPEC as SCAFFOLD_DLL_DEVICE_SERVICE,
)
from .mixed_signal.scaffold_dll_device import DllDeviceScaffold, scaffold_dll_device
from .mixed_signal.scaffold_python_device import (
    SERVICE_SPEC as SCAFFOLD_PYTHON_DEVICE_SERVICE,
)
from .mixed_signal.scaffold_python_device import (
    PythonDeviceScaffold,
    scaffold_python_device,
)
from .mixed_signal.scaffold_socket_device import (
    SERVICE_SPEC as SCAFFOLD_SOCKET_DEVICE_SERVICE,
)
from .mixed_signal.scaffold_socket_device import (
    SocketDeviceScaffold,
    scaffold_socket_device,
)
from .mixed_signal.scaffold_verilog_device import (
    SERVICE_SPEC as SCAFFOLD_VERILOG_DEVICE_SERVICE,
)
from .mixed_signal.scaffold_verilog_device import (
    VerilogDeviceScaffold,
    scaffold_verilog_device,
)
from .protocol.describe_protocol_support import (
    SERVICE_SPEC as DESCRIBE_PROTOCOL_SUPPORT_SERVICE,
)
from .protocol.describe_protocol_support import (
    ProtocolSupport,
    describe_protocol_support,
)
from .protocol.scaffold_i2c_device import (
    SERVICE_SPEC as SCAFFOLD_I2C_DEVICE_SERVICE,
)
from .protocol.scaffold_i2c_device import I2cDeviceScaffold, scaffold_i2c_device
from .protocol.scaffold_spi_device import (
    SERVICE_SPEC as SCAFFOLD_SPI_DEVICE_SERVICE,
)
from .protocol.scaffold_spi_device import SpiDeviceScaffold, scaffold_spi_device
from .recipes.describe_reference_circuit_recipe import (
    SERVICE_SPEC as DESCRIBE_REFERENCE_CIRCUIT_RECIPE_SERVICE,
)
from .recipes.describe_reference_circuit_recipe import (
    ReferenceCircuitRecipeDescription,
    describe_reference_circuit_recipe,
)
from .recipes.list_reference_circuit_recipes import (
    SERVICE_SPEC as LIST_REFERENCE_CIRCUIT_RECIPES_SERVICE,
)
from .recipes.list_reference_circuit_recipes import (
    ReferenceCircuitRecipeList,
    list_reference_circuit_recipes,
)
from .remote.close_remote_session import SERVICE_SPEC as CLOSE_REMOTE_SESSION_SERVICE
from .remote.close_remote_session import RemoteSessionClosure
from .remote.download_remote_artifacts import SERVICE_SPEC as DOWNLOAD_REMOTE_ARTIFACTS_SERVICE
from .remote.download_remote_artifacts import RemoteArtifactDownload
from .remote.poll_remote_run import SERVICE_SPEC as POLL_REMOTE_RUN_SERVICE
from .remote.poll_remote_run import RemoteRunStatus
from .remote.submit_remote_simulation import SERVICE_SPEC as SUBMIT_REMOTE_SIMULATION_SERVICE
from .remote.submit_remote_simulation import RemoteSimulationSubmission
from .schematic.add_component import SERVICE_SPEC as ADD_COMPONENT_SERVICE
from .schematic.add_component import AddedComponent, add_component
from .schematic.add_component_symbol_drawing import (
    SERVICE_SPEC as ADD_COMPONENT_SYMBOL_DRAWING_SERVICE,
)
from .schematic.add_component_symbol_drawing import (
    ComponentSymbolDrawingAdd,
    add_component_symbol_drawing,
)
from .schematic.add_instruction import SERVICE_SPEC as ADD_INSTRUCTION_SERVICE
from .schematic.add_instruction import InstructionAdd, add_instruction
from .schematic.add_junction import SERVICE_SPEC as ADD_JUNCTION_SERVICE
from .schematic.add_junction import AddedJunction, add_junction
from .schematic.add_net_label import SERVICE_SPEC as ADD_NET_LABEL_SERVICE
from .schematic.add_net_label import AddedNetLabel, add_net_label
from .schematic.add_wire import SERVICE_SPEC as ADD_WIRE_SERVICE
from .schematic.add_wire import AddedWire, add_wire
from .schematic.create_schematic import SERVICE_SPEC as CREATE_SCHEMATIC_SERVICE
from .schematic.create_schematic import CreatedSchematic, create_schematic
from .schematic.create_starter_schematic import SERVICE_SPEC as CREATE_STARTER_SCHEMATIC_SERVICE
from .schematic.create_starter_schematic import (
    CreatedStarterSchematic,
    create_starter_schematic,
)
from .schematic.describe_edit_capability import (
    SERVICE_SPEC as DESCRIBE_EDIT_CAPABILITY_SERVICE,
)
from .schematic.describe_edit_capability import (
    EditCapability,
    describe_edit_capability,
)
from .schematic.describe_schematic_edit_support import (
    SERVICE_SPEC as DESCRIBE_SCHEMATIC_EDIT_SUPPORT_SERVICE,
)
from .schematic.describe_schematic_edit_support import (
    IntentEntry,
    SchematicEditSupport,
    describe_schematic_edit_support,
)
from .schematic.describe_topology_authoring_support import (
    SERVICE_SPEC as DESCRIBE_TOPOLOGY_AUTHORING_SUPPORT_SERVICE,
)
from .schematic.describe_topology_authoring_support import (
    TopologyAuthoringSupport,
    TopologyCapabilityEntry,
    describe_topology_authoring_support,
)
from .schematic.inspect_schematic import SERVICE_SPEC as INSPECT_SCHEMATIC_SERVICE
from .schematic.inspect_schematic import (
    SchematicComponentSummary,
    SchematicInspection,
    inspect_schematic,
)
from .schematic.list_components import SERVICE_SPEC as LIST_COMPONENTS_SERVICE
from .schematic.list_components import ComponentCatalog, ComponentSummary, list_components
from .schematic.materialize_reference_circuit import (
    SERVICE_SPEC as MATERIALIZE_REFERENCE_CIRCUIT_SERVICE,
)
from .schematic.materialize_reference_circuit import (
    MaterializedFile,
    MaterializedReferenceCircuit,
    materialize_reference_circuit,
)
from .schematic.read_component import SERVICE_SPEC as READ_COMPONENT_SERVICE
from .schematic.read_component import ComponentRead, read_component
from .schematic.read_component_symbol import SERVICE_SPEC as READ_COMPONENT_SYMBOL_SERVICE
from .schematic.read_component_symbol import ComponentSymbolRead, read_component_symbol
from .schematic.remove_component import (
    SERVICE_SPEC as REMOVE_COMPONENT_SERVICE,
)
from .schematic.remove_component import RemovedComponent, remove_component
from .schematic.remove_component_symbol_drawing import (
    SERVICE_SPEC as REMOVE_COMPONENT_SYMBOL_DRAWING_SERVICE,
)
from .schematic.remove_component_symbol_drawing import (
    ComponentSymbolDrawingRemoval,
    remove_component_symbol_drawing,
)
from .schematic.remove_instruction import SERVICE_SPEC as REMOVE_INSTRUCTION_SERVICE
from .schematic.remove_instruction import InstructionRemoval, remove_instruction
from .schematic.rename_component_reference import (
    SERVICE_SPEC as RENAME_COMPONENT_REFERENCE_SERVICE,
)
from .schematic.rename_component_reference import (
    RenamedComponentReference,
    rename_component_reference,
)
from .schematic.save_schematic_as import SERVICE_SPEC as SAVE_SCHEMATIC_AS_SERVICE
from .schematic.save_schematic_as import SavedSchematic, save_schematic_as
from .schematic.set_component_parameters import SERVICE_SPEC as SET_COMPONENT_PARAMETERS_SERVICE
from .schematic.set_component_parameters import ComponentParameterUpdate, set_component_parameters
from .schematic.set_component_rotation import SERVICE_SPEC as SET_COMPONENT_ROTATION_SERVICE
from .schematic.set_component_rotation import ComponentRotationUpdate, set_component_rotation
from .schematic.set_component_symbol_drawing import (
    SERVICE_SPEC as SET_COMPONENT_SYMBOL_DRAWING_SERVICE,
)
from .schematic.set_component_symbol_drawing import (
    ComponentSymbolDrawingUpdate,
    set_component_symbol_drawing,
)
from .schematic.set_component_symbol_pin import SERVICE_SPEC as SET_COMPONENT_SYMBOL_PIN_SERVICE
from .schematic.set_component_symbol_pin import ComponentSymbolPinUpdate, set_component_symbol_pin
from .schematic.set_component_symbol_text import SERVICE_SPEC as SET_COMPONENT_SYMBOL_TEXT_SERVICE
from .schematic.set_component_symbol_text import (
    ComponentSymbolTextUpdate,
    set_component_symbol_text,
)
from .schematic.set_component_value import SERVICE_SPEC as SET_COMPONENT_VALUE_SERVICE
from .schematic.set_component_value import ComponentValueUpdate, set_component_value
from .schematic.set_element_model import SERVICE_SPEC as SET_ELEMENT_MODEL_SERVICE
from .schematic.set_element_model import ElementModelUpdate, set_element_model
from .schematic.set_parameter import SERVICE_SPEC as SET_PARAMETER_SERVICE
from .schematic.set_parameter import SchematicParameterUpdate, set_parameter
from .service_spec import ServicePhase, ServiceSpec
from .simulation.generate_netlist import SERVICE_SPEC as GENERATE_NETLIST_SERVICE
from .simulation.generate_netlist import GeneratedNetlist, generate_netlist
from .simulation.list_plot_suggestions import SERVICE_SPEC as LIST_PLOT_SUGGESTIONS_SERVICE
from .simulation.list_plot_suggestions import (
    PlotSuggestion,
    PlotSuggestionCatalog,
    list_plot_suggestions,
)
from .simulation.prepare_bode_analysis import SERVICE_SPEC as PREPARE_BODE_ANALYSIS_SERVICE
from .simulation.prepare_bode_analysis import PreparedBodeAnalysis, prepare_bode_analysis
from .simulation.prepare_monte_carlo import SERVICE_SPEC as PREPARE_MONTE_CARLO_SERVICE
from .simulation.prepare_monte_carlo import (
    MonteCarloComponentValue,
    MonteCarloParameter,
    MonteCarloSample,
    NativeMonteCarloStage,
    PreparedMonteCarlo,
    load_prepared_monte_carlo,
    prepare_monte_carlo,
    save_prepared_monte_carlo,
)
from .simulation.prepare_worst_case import SERVICE_SPEC as PREPARE_WORST_CASE_SERVICE
from .simulation.prepare_worst_case import (
    PreparedWorstCase,
    WorstCaseCase,
    WorstCaseComponentValue,
    WorstCaseMode,
    WorstCaseParameter,
    load_prepared_worst_case,
    prepare_worst_case,
    save_prepared_worst_case,
)
from .simulation.run_model_sweep import SERVICE_SPEC as RUN_MODEL_SWEEP_SERVICE
from .simulation.run_model_sweep import run_model_sweep
from .simulation.run_monte_carlo import SERVICE_SPEC as RUN_MONTE_CARLO_SERVICE
from .simulation.run_monte_carlo import run_monte_carlo
from .simulation.run_param_sweep import SERVICE_SPEC as RUN_PARAM_SWEEP_SERVICE
from .simulation.run_param_sweep import run_param_sweep
from .simulation.run_simulation import SERVICE_SPEC as RUN_SIMULATION_SERVICE
from .simulation.run_simulation import SimulationRun, run_simulation
from .simulation.run_value_sweep import SERVICE_SPEC as RUN_VALUE_SWEEP_SERVICE
from .simulation.run_value_sweep import run_value_sweep
from .simulation.run_worst_case import SERVICE_SPEC as RUN_WORST_CASE_SERVICE
from .simulation.run_worst_case import run_worst_case
from .simulation.save_netlist_copy import SERVICE_SPEC as SAVE_NETLIST_COPY_SERVICE
from .simulation.save_netlist_copy import SavedNetlistCopy, save_netlist_copy
from .simulation.summarize_tolerance_analysis import (
    SERVICE_SPEC as SUMMARIZE_TOLERANCE_ANALYSIS_SERVICE,
)
from .simulation.summarize_tolerance_analysis import (
    ToleranceAnalysisSummary,
    ToleranceComponentValueSummary,
    ToleranceMeasureSummary,
    ToleranceParameterSummary,
    summarize_tolerance_analysis,
)
from .subcircuit.list_subcircuits import SERVICE_SPEC as LIST_SUBCIRCUITS_SERVICE
from .subcircuit.list_subcircuits import SubcircuitCatalog, SubcircuitSummary, list_subcircuits
from .subcircuit.read_subcircuit import SERVICE_SPEC as READ_SUBCIRCUIT_SERVICE
from .subcircuit.read_subcircuit import (
    SubcircuitComponentSummary,
    SubcircuitRead,
    SubcircuitScope,
    read_subcircuit,
)
from .subcircuit.set_subcircuit_component_parameters import (
    SERVICE_SPEC as SET_SUBCIRCUIT_COMPONENT_PARAMETERS_SERVICE,
)
from .subcircuit.set_subcircuit_component_parameters import (
    SubcircuitComponentParameterUpdate,
    set_subcircuit_component_parameters,
)
from .subcircuit.set_subcircuit_component_value import (
    SERVICE_SPEC as SET_SUBCIRCUIT_COMPONENT_VALUE_SERVICE,
)
from .subcircuit.set_subcircuit_component_value import (
    SubcircuitComponentValueUpdate,
    set_subcircuit_component_value,
)
from .waveform.compute_thd import SERVICE_SPEC as COMPUTE_THD_SERVICE
from .waveform.compute_thd import ThdAnalysis, ThdHarmonic, compute_thd
from .waveform.export_fft_spectrum import SERVICE_SPEC as EXPORT_FFT_SPECTRUM_SERVICE
from .waveform.export_fft_spectrum import FftSpectrumExport, export_fft_spectrum
from .waveform.filter_device_operating_points import (
    SERVICE_SPEC as FILTER_DEVICE_OPERATING_POINTS_SERVICE,
)
from .waveform.filter_device_operating_points import (
    DeviceOperatingPointFilters,
    FilteredDeviceOperatingPointCatalog,
    filter_device_operating_points,
)
from .waveform.list_measures import SERVICE_SPEC as LIST_MEASURES_SERVICE
from .waveform.list_measures import MeasureCatalog, MeasureSummary, list_measures
from .waveform.list_signals import SERVICE_SPEC as LIST_SIGNALS_SERVICE
from .waveform.list_signals import SignalCatalog, SignalSummary, list_signals
from .waveform.list_steps import SERVICE_SPEC as LIST_STEPS_SERVICE
from .waveform.list_steps import StepCatalog, StepSummary, list_steps
from .waveform.measure_bode_response import SERVICE_SPEC as MEASURE_BODE_RESPONSE_SERVICE
from .waveform.measure_bode_response import BodeMeasurement, BodeSample, measure_bode_response
from .waveform.measure_waveform import SERVICE_SPEC as MEASURE_WAVEFORM_SERVICE
from .waveform.measure_waveform import MeasurementOperation, WaveformMeasurement, measure_waveform
from .waveform.plot_waveforms import SERVICE_SPEC as PLOT_WAVEFORMS_SERVICE
from .waveform.plot_waveforms import WaveformPlot, plot_waveforms
from .waveform.read_device_operating_points import (
    SERVICE_SPEC as READ_DEVICE_OPERATING_POINTS_SERVICE,
)
from .waveform.read_device_operating_points import (
    DeviceOperatingPoint,
    DeviceOperatingPointCatalog,
    NodeVoltage,
    OperatingPointGroup,
    OperatingPointMetric,
    read_device_operating_points,
)
from .waveform.read_log import SERVICE_SPEC as READ_LOG_SERVICE
from .waveform.read_log import LogInspection, LogMeasurement, LogStepVariable, read_log
from .waveform.read_measures import SERVICE_SPEC as READ_MEASURES_SERVICE
from .waveform.read_measures import MeasureRead, MeasureResult, MeasureRow, read_measures
from .waveform.read_waveform import SERVICE_SPEC as READ_WAVEFORM_SERVICE
from .waveform.read_waveform import WaveformRead, read_waveform
from .waveform.summarize_device_operating_points import (
    SERVICE_SPEC as SUMMARIZE_DEVICE_OPERATING_POINTS_SERVICE,
)
from .waveform.summarize_device_operating_points import (
    DeviceOperatingPointExtremum,
    DeviceOperatingPointSummary,
    OperatingPointFamilySummary,
    summarize_device_operating_points,
)
from .workspace.write_workspace_text_file import (
    SERVICE_SPEC as WRITE_WORKSPACE_TEXT_FILE_SERVICE,
)
from .workspace.write_workspace_text_file import (
    WrittenWorkspaceTextFile,
    write_workspace_text_file,
)

DESCRIBE_SERVER_CAPABILITIES_SERVICE = ServiceSpec(
    name="describe_server_capabilities",
    title="Describe Server Capabilities",
    summary=("Report server-level backend availability, degraded tool groups, and feature flags."),
    phase="implemented",
)

SCHEMATIC_SERVICE_SPECS = discover_package_service_specs("schematic")

SUBCIRCUIT_SERVICE_SPECS = discover_package_service_specs("subcircuit")

SIMULATION_SERVICE_SPECS = discover_package_service_specs("simulation")

BATCH_SERVICE_SPECS = discover_package_service_specs("batch")

SERVER_SERVICE_SPECS = (DESCRIBE_SERVER_CAPABILITIES_SERVICE,)

REMOTE_SERVICE_SPECS = discover_package_service_specs("remote")

WAVEFORM_SERVICE_SPECS = discover_package_service_specs("waveform")

ARTIFACT_SERVICE_SPECS = discover_package_service_specs("artifacts")

MIXED_SIGNAL_SERVICE_SPECS = discover_package_service_specs("mixed_signal")

PROTOCOL_SERVICE_SPECS = discover_package_service_specs("protocol")

LIVE_GUI_SERVICE_SPECS = discover_package_service_specs("live_gui")

SERVICE_SPECS: tuple[ServiceSpec, ...] = build_service_spec_catalog(
    extra_specs=SERVER_SERVICE_SPECS,
)

_LEGACY_MODULE_ALIASES: dict[str, str] = {
    "_batch_manager": "qspice_mcp.services._internals.batch_manager",
    "_schematic_editor_backend": "qspice_mcp.services._backends.schematic_editor",
    "_schematic_edits": "qspice_mcp.services._internals.schematic_edits",
    "_simulation_batch": "qspice_mcp.services._internals.simulation_batch",
    "_step_filters": "qspice_mcp.services._internals.step_filters",
    "_waveform_backend": "qspice_mcp.services._backends.waveform",
}


def _register_legacy_module_aliases() -> None:
    for legacy_name, target in _LEGACY_MODULE_ALIASES.items():
        sys.modules.setdefault(f"{__name__}.{legacy_name}", import_module(target))


def get_service_specs() -> tuple[ServiceSpec, ...]:
    """Return the planned service catalog in registration order."""

    return SERVICE_SPECS


_register_legacy_module_aliases()


__all__ = [
    "ADD_COMPONENT_SERVICE",
    "ADD_COMPONENT_SYMBOL_DRAWING_SERVICE",
    "ADD_INSTRUCTION_SERVICE",
    "ADD_JUNCTION_SERVICE",
    "ADD_NET_LABEL_SERVICE",
    "ADD_WIRE_SERVICE",
    "ARTIFACT_SERVICE_SPECS",
    "BATCH_SERVICE_SPECS",
    "BUILD_DLL_DEVICE_SERVICE",
    "CANCEL_BATCH_SERVICE",
    "CLOSE_LIVE_GUI_SESSION_SERVICE",
    "CLOSE_REMOTE_SESSION_SERVICE",
    "COLLECT_BATCH_RESULTS_SERVICE",
    "COMPARE_WAVEFORMS_SERVICE",
    "COMPUTE_THD_SERVICE",
    "CREATE_SCHEMATIC_SERVICE",
    "CREATE_STARTER_SCHEMATIC_SERVICE",
    "DESCRIBE_EDIT_CAPABILITY_SERVICE",
    "DESCRIBE_LIVE_GUI_SUPPORT_SERVICE",
    "DESCRIBE_MIXED_SIGNAL_SUPPORT_SERVICE",
    "DESCRIBE_PROTOCOL_SUPPORT_SERVICE",
    "DESCRIBE_QUX_EXPORT_SUPPORT_SERVICE",
    "DESCRIBE_REFERENCE_CIRCUIT_RECIPE_SERVICE",
    "DESCRIBE_SCHEMATIC_EDIT_SUPPORT_SERVICE",
    "DESCRIBE_SERVER_CAPABILITIES_SERVICE",
    "DESCRIBE_TOPOLOGY_AUTHORING_SUPPORT_SERVICE",
    "DOWNLOAD_REMOTE_ARTIFACTS_SERVICE",
    "EXPORT_DERIVED_RAW_SERVICE",
    "EXPORT_FFT_SPECTRUM_SERVICE",
    "EXPORT_MEASURES_CSV_SERVICE",
    "EXPORT_TOUCHSTONE_S2P_SERVICE",
    "EXPORT_WAVEFORM_ASCII_SERVICE",
    "EXPORT_WAVEFORM_CSV_SERVICE",
    "EXPORT_WAVEFORM_SPICE_SERVICE",
    "FILTER_DEVICE_OPERATING_POINTS_SERVICE",
    "GENERATE_DLL_VARIABLES_SERVICE",
    "GENERATE_NETLIST_SERVICE",
    "GET_BATCH_STATUS_SERVICE",
    "INSPECT_SCHEMATIC_SERVICE",
    "LAUNCH_LIVE_GUI_SESSION_SERVICE",
    "LIST_COMPONENTS_SERVICE",
    "LIST_MEASURES_SERVICE",
    "LIST_PLOT_SUGGESTIONS_SERVICE",
    "LIST_REFERENCE_CIRCUIT_RECIPES_SERVICE",
    "LIST_SIGNALS_SERVICE",
    "LIST_STEPS_SERVICE",
    "LIST_SUBCIRCUITS_SERVICE",
    "LIST_WORKFLOW_INSTRUCTIONS_SERVICE",
    "LIVE_GUI_SERVICE_SPECS",
    "MATERIALIZE_REFERENCE_CIRCUIT_SERVICE",
    "MEASURE_BODE_RESPONSE_SERVICE",
    "MEASURE_WAVEFORM_SERVICE",
    "MERGE_WAVEFORMS_SERVICE",
    "MIXED_SIGNAL_SERVICE_SPECS",
    "OPEN_SCHEMATIC_IN_GUI_SERVICE",
    "PLOT_WAVEFORMS_SERVICE",
    "POLL_LIVE_GUI_SESSION_EVENTS_SERVICE",
    "POLL_LIVE_GUI_SESSION_SERVICE",
    "POLL_REMOTE_RUN_SERVICE",
    "PREPARE_BODE_ANALYSIS_SERVICE",
    "PREPARE_MONTE_CARLO_SERVICE",
    "PREPARE_WORST_CASE_SERVICE",
    "READ_COMPONENT_SERVICE",
    "READ_COMPONENT_SYMBOL_SERVICE",
    "READ_DEVICE_OPERATING_POINTS_SERVICE",
    "READ_LOG_SERVICE",
    "READ_MEASURES_SERVICE",
    "READ_SUBCIRCUIT_SERVICE",
    "READ_WAVEFORM_SERVICE",
    "READ_WORKFLOW_INSTRUCTION_SERVICE",
    "REFRESH_SCHEMATIC_IN_GUI_SERVICE",
    "REMOTE_SERVICE_SPECS",
    "REMOVE_COMPONENT_SERVICE",
    "REMOVE_COMPONENT_SYMBOL_DRAWING_SERVICE",
    "REMOVE_INSTRUCTION_SERVICE",
    "RENAME_COMPONENT_REFERENCE_SERVICE",
    "RUN_MODEL_SWEEP_SERVICE",
    "RUN_MONTE_CARLO_SERVICE",
    "RUN_PARAM_SWEEP_SERVICE",
    "RUN_SIMULATION_SERVICE",
    "RUN_VALUE_SWEEP_SERVICE",
    "RUN_WORST_CASE_SERVICE",
    "SAVE_NETLIST_COPY_SERVICE",
    "SAVE_SCHEMATIC_AS_SERVICE",
    "SCAFFOLD_DLL_DEVICE_SERVICE",
    "SCAFFOLD_I2C_DEVICE_SERVICE",
    "SCAFFOLD_LIVE_GUI_SESSION_SERVICE",
    "SCAFFOLD_PYTHON_DEVICE_SERVICE",
    "SCAFFOLD_SOCKET_DEVICE_SERVICE",
    "SCAFFOLD_SPI_DEVICE_SERVICE",
    "SCAFFOLD_VERILOG_DEVICE_SERVICE",
    "SCHEMATIC_SERVICE_SPECS",
    "SEND_LIVE_GUI_SESSION_COMMAND_SERVICE",
    "SERVER_SERVICE_SPECS",
    "SERVICE_SPECS",
    "SET_COMPONENT_PARAMETERS_SERVICE",
    "SET_COMPONENT_ROTATION_SERVICE",
    "SET_COMPONENT_SYMBOL_DRAWING_SERVICE",
    "SET_COMPONENT_SYMBOL_PIN_SERVICE",
    "SET_COMPONENT_SYMBOL_TEXT_SERVICE",
    "SET_COMPONENT_VALUE_SERVICE",
    "SET_ELEMENT_MODEL_SERVICE",
    "SET_PARAMETER_SERVICE",
    "SET_SUBCIRCUIT_COMPONENT_PARAMETERS_SERVICE",
    "SET_SUBCIRCUIT_COMPONENT_VALUE_SERVICE",
    "SIMULATION_SERVICE_SPECS",
    "SUBCIRCUIT_SERVICE_SPECS",
    "SUBMIT_BATCH_SERVICE",
    "SUBMIT_REMOTE_SIMULATION_SERVICE",
    "SUMMARIZE_BATCH_SERVICE",
    "SUMMARIZE_DEVICE_OPERATING_POINTS_SERVICE",
    "SUMMARIZE_TOLERANCE_ANALYSIS_SERVICE",
    "WAVEFORM_SERVICE_SPECS",
    "WRITE_WORKSPACE_TEXT_FILE_SERVICE",
    "AddedComponent",
    "AddedJunction",
    "AddedNetLabel",
    "AddedWire",
    "BatchCancellation",
    "BatchCollection",
    "BatchRunSummary",
    "BatchStatus",
    "BatchSubmission",
    "BatchSummary",
    "BodeMeasurement",
    "BodeSample",
    "BuiltDllDevice",
    "ComponentCatalog",
    "ComponentParameterUpdate",
    "ComponentRead",
    "ComponentRotationUpdate",
    "ComponentSummary",
    "ComponentSymbolDrawingAdd",
    "ComponentSymbolDrawingRemoval",
    "ComponentSymbolDrawingUpdate",
    "ComponentSymbolPinUpdate",
    "ComponentSymbolRead",
    "ComponentSymbolTextUpdate",
    "ComponentValueUpdate",
    "CreatedSchematic",
    "CreatedStarterSchematic",
    "DerivedRawExport",
    "DeviceOperatingPoint",
    "DeviceOperatingPointCatalog",
    "DeviceOperatingPointExtremum",
    "DeviceOperatingPointFilters",
    "DeviceOperatingPointSummary",
    "DllDeviceScaffold",
    "DllVariableExport",
    "EditCapability",
    "ElementModelUpdate",
    "FftSpectrumExport",
    "FilteredDeviceOperatingPointCatalog",
    "GeneratedNetlist",
    "I2cDeviceScaffold",
    "InstructionAdd",
    "InstructionRemoval",
    "IntentEntry",
    "LiveGuiSessionClosure",
    "LiveGuiSessionCommandDispatch",
    "LiveGuiSessionEvent",
    "LiveGuiSessionEventPoll",
    "LiveGuiSessionLaunch",
    "LiveGuiSessionScaffold",
    "LiveGuiSessionStatus",
    "LiveGuiSupport",
    "LogInspection",
    "LogMeasurement",
    "LogStepVariable",
    "MaterializedFile",
    "MaterializedReferenceCircuit",
    "MeasureCatalog",
    "MeasureCsvExport",
    "MeasureRead",
    "MeasureResult",
    "MeasureRow",
    "MeasureSummary",
    "MeasurementOperation",
    "MergedWaveformExport",
    "MixedSignalSupport",
    "MonteCarloComponentValue",
    "MonteCarloParameter",
    "MonteCarloSample",
    "NativeMonteCarloStage",
    "NodeVoltage",
    "OpenedSchematicInGui",
    "OperatingPointFamilySummary",
    "OperatingPointGroup",
    "OperatingPointMetric",
    "PlotSuggestion",
    "PlotSuggestionCatalog",
    "PreparedBodeAnalysis",
    "PreparedMonteCarlo",
    "PreparedWorstCase",
    "ProtocolSupport",
    "PythonDeviceScaffold",
    "QuxExportSupport",
    "QuxWaveformExport",
    "ReferenceCircuitRecipeDescription",
    "ReferenceCircuitRecipeList",
    "RefreshedSchematicInGui",
    "RemoteArtifactDownload",
    "RemoteRunStatus",
    "RemoteSessionClosure",
    "RemoteSimulationSubmission",
    "RemovedComponent",
    "RenamedComponentReference",
    "SavedNetlistCopy",
    "SavedSchematic",
    "SchematicComponentSummary",
    "SchematicEditSupport",
    "SchematicInspection",
    "SchematicParameterUpdate",
    "ServicePhase",
    "ServiceSpec",
    "SignalCatalog",
    "SignalSummary",
    "SimulationBatch",
    "SimulationBatchRun",
    "SimulationRun",
    "SocketDeviceScaffold",
    "SpiDeviceScaffold",
    "StepCatalog",
    "StepSummary",
    "SubcircuitCatalog",
    "SubcircuitComponentParameterUpdate",
    "SubcircuitComponentSummary",
    "SubcircuitComponentValueUpdate",
    "SubcircuitRead",
    "SubcircuitScope",
    "SubcircuitSummary",
    "ThdAnalysis",
    "ThdHarmonic",
    "ToleranceAnalysisSummary",
    "ToleranceComponentValueSummary",
    "ToleranceMeasureSummary",
    "ToleranceParameterSummary",
    "TopologyAuthoringSupport",
    "TopologyCapabilityEntry",
    "VerilogDeviceScaffold",
    "WaveformComparison",
    "WaveformComparisonRun",
    "WaveformMeasurement",
    "WaveformMergeInput",
    "WaveformPlot",
    "WaveformRead",
    "WorkflowInstructionDocument",
    "WorkflowInstructionList",
    "WorstCaseCase",
    "WorstCaseComponentValue",
    "WorstCaseMode",
    "WorstCaseParameter",
    "WrittenWorkspaceTextFile",
    "add_component",
    "add_component_symbol_drawing",
    "add_instruction",
    "add_junction",
    "add_net_label",
    "add_wire",
    "build_dll_device",
    "compare_waveforms",
    "compute_thd",
    "create_schematic",
    "create_starter_schematic",
    "describe_edit_capability",
    "describe_live_gui_support",
    "describe_mixed_signal_support",
    "describe_protocol_support",
    "describe_qux_export_support",
    "describe_reference_circuit_recipe",
    "describe_schematic_edit_support",
    "describe_topology_authoring_support",
    "export_derived_raw",
    "export_fft_spectrum",
    "export_measures_csv",
    "export_touchstone_s2p",
    "export_waveform_ascii",
    "export_waveform_csv",
    "export_waveform_spice",
    "filter_device_operating_points",
    "generate_dll_variables",
    "generate_netlist",
    "get_service_specs",
    "inspect_schematic",
    "list_components",
    "list_measures",
    "list_plot_suggestions",
    "list_reference_circuit_recipes",
    "list_signals",
    "list_steps",
    "list_subcircuits",
    "list_workflow_instructions",
    "load_prepared_monte_carlo",
    "load_prepared_worst_case",
    "materialize_reference_circuit",
    "measure_bode_response",
    "measure_waveform",
    "merge_waveforms",
    "open_schematic_in_gui",
    "plot_waveforms",
    "prepare_bode_analysis",
    "prepare_monte_carlo",
    "prepare_worst_case",
    "read_component",
    "read_component_symbol",
    "read_device_operating_points",
    "read_log",
    "read_measures",
    "read_subcircuit",
    "read_waveform",
    "read_workflow_instruction",
    "refresh_schematic_in_gui",
    "remove_component",
    "remove_component_symbol_drawing",
    "remove_instruction",
    "rename_component_reference",
    "resolve_workspace_path",
    "run_model_sweep",
    "run_monte_carlo",
    "run_param_sweep",
    "run_simulation",
    "run_value_sweep",
    "run_worst_case",
    "save_netlist_copy",
    "save_prepared_monte_carlo",
    "save_prepared_worst_case",
    "save_schematic_as",
    "scaffold_dll_device",
    "scaffold_i2c_device",
    "scaffold_live_gui_session",
    "scaffold_python_device",
    "scaffold_socket_device",
    "scaffold_spi_device",
    "scaffold_verilog_device",
    "set_component_parameters",
    "set_component_rotation",
    "set_component_symbol_drawing",
    "set_component_symbol_pin",
    "set_component_symbol_text",
    "set_component_value",
    "set_element_model",
    "set_parameter",
    "set_subcircuit_component_parameters",
    "set_subcircuit_component_value",
    "summarize_batch",
    "summarize_device_operating_points",
    "summarize_tolerance_analysis",
    "validate_existing_file",
    "validate_time_window",
    "write_workspace_text_file",
]
