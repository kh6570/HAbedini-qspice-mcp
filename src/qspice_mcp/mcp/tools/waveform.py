"""Waveform, log, and measurement tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

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
from qspice_mcp.services.waveform.measure_stability_margins import (
    measure_stability_margins as measure_stability_margins_service,
)
from qspice_mcp.services.waveform.measure_waveform import (
    measure_waveform as measure_waveform_service,
)
from qspice_mcp.services.waveform.plot_waveforms import plot_waveforms as plot_waveforms_service
from qspice_mcp.services.waveform.read_device_operating_points import (
    read_device_operating_points as read_device_operating_points_service,
)
from qspice_mcp.services.waveform.read_log import read_log as read_log_service
from qspice_mcp.services.waveform.read_measures import read_measures as read_measures_service
from qspice_mcp.services.waveform.read_waveform import read_waveform as read_waveform_service
from qspice_mcp.services.waveform.summarize_device_operating_points import (
    summarize_device_operating_points as summarize_device_operating_points_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

WaveformComponent = Literal["auto", "real", "imag", "magnitude", "phase"]
MeasurementOperation = Literal[
    "min",
    "max",
    "mean",
    "rms",
    "peak_to_peak",
    "abs_max",
    "start",
    "end",
    "integral",
]

WAVEFORM_HANDLER_NAMES = (
    "list_steps",
    "list_signals",
    "read_device_operating_points",
    "filter_device_operating_points",
    "summarize_device_operating_points",
    "read_waveform",
    "measure_waveform",
    "measure_bode_response",
    "measure_stability_margins",
    "compute_thd",
    "export_fft_spectrum",
    "plot_waveforms",
    "list_measures",
    "read_measures",
    "read_log",
)


class WaveformToolMixin:
    """Handlers for waveform, log, and measurement tools."""

    def list_steps(self: _RuntimeWithSettings, raw_path: str) -> dict[str, object]:
        inspection = list_steps_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(inspection)

    def list_signals(
        self: _RuntimeWithSettings,
        raw_path: str,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
    ) -> dict[str, object]:
        inspection = list_signals_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            step=step,
            step_filters=step_filters,
        )
        return to_json_object(inspection)

    def read_device_operating_points(
        self: _RuntimeWithSettings,
        raw_path: str,
        netlist_path: str | None = None,
    ) -> dict[str, object]:
        inspection = read_device_operating_points_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            netlist_path=netlist_path,
        )
        return to_json_object(inspection)

    def filter_device_operating_points(
        self: _RuntimeWithSettings,
        raw_path: str,
        netlist_path: str | None = None,
        families: list[str] | None = None,
        models: list[str] | None = None,
        references: list[str] | None = None,
        reference_pattern: str | None = None,
        metric_names: list[str] | None = None,
    ) -> dict[str, object]:
        inspection = filter_device_operating_points_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            netlist_path=netlist_path,
            families=families,
            models=models,
            references=references,
            reference_pattern=reference_pattern,
            metric_names=metric_names,
        )
        return to_json_object(inspection)

    def summarize_device_operating_points(
        self: _RuntimeWithSettings,
        raw_path: str,
        netlist_path: str | None = None,
    ) -> dict[str, object]:
        inspection = summarize_device_operating_points_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            netlist_path=netlist_path,
        )
        return to_json_object(inspection)

    def read_waveform(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
        max_points: int | None = None,
        max_bytes: int | None = None,
    ) -> dict[str, object]:
        inspection = read_waveform_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
            max_points=max_points,
            max_bytes=max_bytes,
        )
        return to_json_object(inspection)

    def measure_waveform(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        operation: MeasurementOperation,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> dict[str, object]:
        inspection = measure_waveform_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            operation=operation,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        return to_json_object(inspection)

    def measure_bode_response(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        frequencies_hz: list[float],
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
    ) -> dict[str, object]:
        inspection = measure_bode_response_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            frequencies_hz=frequencies_hz,
            step=step,
            step_filters=step_filters,
        )
        return to_json_object(inspection)

    def measure_stability_margins(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
    ) -> dict[str, object]:
        inspection = measure_stability_margins_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            step=step,
            step_filters=step_filters,
        )
        return to_json_object(inspection)

    def compute_thd(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        fundamental_hz: float,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        periods: int = 5,
        harmonics: int = 10,
        t_end: float | None = None,
        samples_per_cycle: int = 512,
    ) -> dict[str, object]:
        inspection = compute_thd_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            fundamental_hz=fundamental_hz,
            step=step,
            step_filters=step_filters,
            component=component,
            periods=periods,
            harmonics=harmonics,
            t_end=t_end,
            samples_per_cycle=samples_per_cycle,
        )
        return to_json_object(inspection)

    def export_fft_spectrum(
        self: _RuntimeWithSettings,
        raw_path: str,
        signal: str,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
        sample_count: int = 4096,
        max_frequency_hz: float | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = export_fft_spectrum_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
            sample_count=sample_count,
            max_frequency_hz=max_frequency_hz,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def plot_waveforms(
        self: _RuntimeWithSettings,
        raw_path: str,
        signals: list[str],
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
        max_points: int | None = None,
        max_bytes: int | None = None,
        output_path: str | None = None,
        fmt: str = "png",
        title: str | None = None,
    ) -> dict[str, object]:
        inspection = plot_waveforms_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signals=signals,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
            max_points=max_points,
            max_bytes=max_bytes,
            output_path=output_path,
            fmt=fmt,
            title=title,
        )
        return to_json_object(inspection)

    def list_measures(
        self: _RuntimeWithSettings,
        log_path: str,
        refresh_measures: bool = True,
        meas_path: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, object]:
        if timeout_s is None:
            inspection = list_measures_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
            )
        else:
            inspection = list_measures_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
                timeout_s=timeout_s,
            )
        return to_json_object(inspection)

    def read_measures(
        self: _RuntimeWithSettings,
        log_path: str,
        measures: list[str] | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        refresh_measures: bool = True,
        meas_path: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, object]:
        if timeout_s is None:
            inspection = read_measures_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                measures=measures,
                step=step,
                step_filters=step_filters,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
            )
        else:
            inspection = read_measures_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                measures=measures,
                step=step,
                step_filters=step_filters,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
                timeout_s=timeout_s,
            )
        return to_json_object(inspection)

    def read_log(
        self: _RuntimeWithSettings,
        log_path: str,
        max_lines: int = 80,
        include_measures: bool = True,
        refresh_measures: bool = True,
        meas_path: str | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, object]:
        if timeout_s is None:
            inspection = read_log_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                max_lines=max_lines,
                include_measures=include_measures,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
            )
        else:
            inspection = read_log_service(
                log_path,
                workspace_root=self.settings.workspace_root,
                settings=self.settings,
                max_lines=max_lines,
                include_measures=include_measures,
                refresh_measures=refresh_measures,
                meas_path=meas_path,
                timeout_s=timeout_s,
            )
        return to_json_object(inspection)


__all__ = [
    "WAVEFORM_HANDLER_NAMES",
    "WaveformToolMixin",
    "compute_thd_service",
    "export_fft_spectrum_service",
    "filter_device_operating_points_service",
    "list_measures_service",
    "list_signals_service",
    "list_steps_service",
    "measure_bode_response_service",
    "measure_stability_margins_service",
    "measure_waveform_service",
    "plot_waveforms_service",
    "read_device_operating_points_service",
    "read_log_service",
    "read_measures_service",
    "read_waveform_service",
    "summarize_device_operating_points_service",
]
