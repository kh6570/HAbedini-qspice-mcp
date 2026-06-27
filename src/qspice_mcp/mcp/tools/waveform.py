"""Waveform, log, and measurement tool handlers."""

from __future__ import annotations

from qspice_mcp.services.waveform.compute_thd import compute_thd as compute_thd_service
from qspice_mcp.services.waveform.export_fft_spectrum import (
    export_fft_spectrum as export_fft_spectrum_service,
)
from qspice_mcp.services.waveform.filter_device_operating_points import (
    filter_device_operating_points as filter_device_operating_points_service,
)
from qspice_mcp.services.waveform.list_measures import list_measures as list_measures_service
from qspice_mcp.services.waveform.list_signals import list_signals as list_signals_service
from qspice_mcp.services.waveform.list_steps import list_steps as list_steps_service
from qspice_mcp.services.waveform.measure_bode_response import (
    measure_bode_response as measure_bode_response_service,
)
from qspice_mcp.services.waveform.measure_efficiency import (
    measure_efficiency as measure_efficiency_service,
)
from qspice_mcp.services.waveform.measure_stability_margins import (
    measure_stability_margins as measure_stability_margins_service,
)
from qspice_mcp.services.waveform.measure_step_response import (
    measure_step_response as measure_step_response_service,
)
from qspice_mcp.services.waveform.measure_waveform import (
    measure_waveform as measure_waveform_service,
)
from qspice_mcp.services.waveform.plot_waveforms import plot_waveforms as plot_waveforms_service
from qspice_mcp.services.waveform.read_device_operating_points import (
    read_device_operating_points as read_device_operating_points_service,
)
from qspice_mcp.services.waveform.read_fourier import read_fourier as read_fourier_service
from qspice_mcp.services.waveform.read_log import read_log as read_log_service
from qspice_mcp.services.waveform.read_measures import read_measures as read_measures_service
from qspice_mcp.services.waveform.read_noise import read_noise as read_noise_service
from qspice_mcp.services.waveform.read_waveform import read_waveform as read_waveform_service
from qspice_mcp.services.waveform.summarize_device_operating_points import (
    summarize_device_operating_points as summarize_device_operating_points_service,
)

__all__ = [
    "compute_thd_service",
    "export_fft_spectrum_service",
    "filter_device_operating_points_service",
    "list_measures_service",
    "list_signals_service",
    "list_steps_service",
    "measure_bode_response_service",
    "measure_efficiency_service",
    "measure_stability_margins_service",
    "measure_step_response_service",
    "measure_waveform_service",
    "plot_waveforms_service",
    "read_device_operating_points_service",
    "read_fourier_service",
    "read_log_service",
    "read_measures_service",
    "read_noise_service",
    "read_waveform_service",
    "summarize_device_operating_points_service",
]
