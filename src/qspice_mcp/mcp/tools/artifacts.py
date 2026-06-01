"""Artifact export and comparison tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from qspice_mcp.services.artifacts.compare_waveforms import (
    compare_waveforms as compare_waveforms_service,
)
from qspice_mcp.services.artifacts.describe_qux_export_support import (
    describe_qux_export_support as describe_qux_export_support_service,
)
from qspice_mcp.services.artifacts.export_derived_raw import (
    export_derived_raw as export_derived_raw_service,
)
from qspice_mcp.services.artifacts.export_measures_csv import (
    export_measures_csv as export_measures_csv_service,
)
from qspice_mcp.services.artifacts.export_touchstone_s2p import (
    export_touchstone_s2p as export_touchstone_s2p_service,
)
from qspice_mcp.services.artifacts.export_waveform_ascii import (
    export_waveform_ascii as export_waveform_ascii_service,
)
from qspice_mcp.services.artifacts.export_waveform_csv import (
    export_waveform_csv as export_waveform_csv_service,
)
from qspice_mcp.services.artifacts.export_waveform_spice import (
    export_waveform_spice as export_waveform_spice_service,
)
from qspice_mcp.services.artifacts.generate_dll_variables import (
    generate_dll_variables as generate_dll_variables_service,
)
from qspice_mcp.services.artifacts.merge_waveforms import (
    merge_waveforms as merge_waveforms_service,
)
from qspice_mcp.services.artifacts.summarize_batch import (
    summarize_batch as summarize_batch_service,
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

ARTIFACT_HANDLER_NAMES = (
    "describe_qux_export_support",
    "export_derived_raw",
    "merge_waveforms",
    "export_waveform_csv",
    "export_waveform_ascii",
    "export_waveform_spice",
    "export_touchstone_s2p",
    "generate_dll_variables",
    "summarize_batch",
    "export_measures_csv",
    "compare_waveforms",
)


class ArtifactToolMixin:
    """Handlers for persisted artifact tools."""

    def describe_qux_export_support(self: _RuntimeWithSettings) -> dict[str, object]:
        inspection = describe_qux_export_support_service(settings=self.settings)
        return to_json_object(inspection)

    def export_derived_raw(
        self: _RuntimeWithSettings,
        raw_path: str,
        signals: list[str],
        output_path: str | None = None,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        all_steps: bool = False,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> dict[str, object]:
        inspection = export_derived_raw_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            signals=signals,
            output_path=output_path,
            step=step,
            step_filters=step_filters,
            all_steps=all_steps,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        return to_json_object(inspection)

    def export_waveform_ascii(
        self: _RuntimeWithSettings,
        raw_path: str,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = export_waveform_ascii_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            expressions=expressions,
            point_count=point_count,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def merge_waveforms(
        self: _RuntimeWithSettings,
        inputs: list[dict[str, object]],
        output_path: str | None = None,
        all_steps: bool = False,
    ) -> dict[str, object]:
        inspection = merge_waveforms_service(
            inputs,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
            all_steps=all_steps,
        )
        return to_json_object(inspection)

    def export_waveform_csv(
        self: _RuntimeWithSettings,
        raw_path: str,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = export_waveform_csv_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            expressions=expressions,
            point_count=point_count,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def export_waveform_spice(
        self: _RuntimeWithSettings,
        raw_path: str,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = export_waveform_spice_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            expressions=expressions,
            point_count=point_count,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def export_touchstone_s2p(
        self: _RuntimeWithSettings,
        raw_path: str,
        expressions: list[str],
        point_count: int | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = export_touchstone_s2p_service(
            raw_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            expressions=expressions,
            point_count=point_count,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def generate_dll_variables(
        self: _RuntimeWithSettings,
        schematic_path: str,
        output_path: str | None = None,
    ) -> dict[str, object]:
        inspection = generate_dll_variables_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            output_path=output_path,
        )
        return to_json_object(inspection)

    def summarize_batch(self: _RuntimeWithSettings, batch_path: str) -> dict[str, object]:
        inspection = summarize_batch_service(
            batch_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(inspection)

    def export_measures_csv(
        self: _RuntimeWithSettings,
        batch_path: str,
        output_path: str | None = None,
        measures: list[str] | None = None,
        refresh_measures: bool = True,
    ) -> dict[str, object]:
        inspection = export_measures_csv_service(
            batch_path,
            workspace_root=self.settings.workspace_root,
            output_path=output_path,
            measures=measures,
            refresh_measures=refresh_measures,
        )
        return to_json_object(inspection)

    def compare_waveforms(
        self: _RuntimeWithSettings,
        batch_path: str,
        signal: str,
        operation: MeasurementOperation,
        baseline_run_index: int = 0,
        step: int | None = None,
        step_filters: dict[str, object] | None = None,
        component: WaveformComponent = "auto",
        t_start: float | None = None,
        t_end: float | None = None,
    ) -> dict[str, object]:
        inspection = compare_waveforms_service(
            batch_path,
            workspace_root=self.settings.workspace_root,
            signal=signal,
            operation=operation,
            baseline_run_index=baseline_run_index,
            step=step,
            step_filters=step_filters,
            component=component,
            t_start=t_start,
            t_end=t_end,
        )
        return to_json_object(inspection)


__all__ = [
    "ARTIFACT_HANDLER_NAMES",
    "ArtifactToolMixin",
    "compare_waveforms_service",
    "describe_qux_export_support_service",
    "export_derived_raw_service",
    "export_measures_csv_service",
    "export_touchstone_s2p_service",
    "export_waveform_ascii_service",
    "export_waveform_csv_service",
    "export_waveform_spice_service",
    "generate_dll_variables_service",
    "merge_waveforms_service",
    "summarize_batch_service",
]
