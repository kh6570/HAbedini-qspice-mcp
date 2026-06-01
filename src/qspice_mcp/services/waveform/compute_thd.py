"""Service for estimating waveform THD over an integer-cycle window."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.waveform import WaveformComponent, load_waveform
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform._spectral import compute_single_sided_fft, prepare_period_window

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_MIN_HARMONICS = 2


@dataclass(frozen=True, slots=True)
class ThdHarmonic:
    """One harmonic contribution used in a THD estimate."""

    harmonic: int
    frequency_hz: float
    amplitude: float
    rms: float
    percent_of_fundamental: float


@dataclass(frozen=True, slots=True)
class ThdAnalysis:
    """THD estimate extracted from one waveform window."""

    raw_path: Path
    plot_name: str | None
    signal: str
    step: int
    component: str
    sample_count: int
    window_start_s: float
    window_end_s: float
    fundamental_hz: float
    harmonics: int
    fundamental_amplitude: float
    fundamental_rms: float
    thd_ratio: float
    thd_percent: float
    contributions: tuple[ThdHarmonic, ...]


SERVICE_SPEC = ServiceSpec(
    name="compute_thd",
    title="Compute THD",
    summary=("Estimate total harmonic distortion over a trailing integer-cycle waveform window."),
    phase="implemented",
)


def compute_thd(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    fundamental_hz: float,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    periods: int = 5,
    harmonics: int = 10,
    t_end: float | None = None,
    samples_per_cycle: int = 512,
) -> ThdAnalysis:
    """Estimate THD from one time-domain waveform over an integer-cycle window."""

    if harmonics < _MIN_HARMONICS:
        raise ValueError("harmonics must be at least 2.")
    waveform = load_waveform(
        raw_path,
        workspace_root=workspace_root.resolve(strict=False),
        signal=signal,
        step=step,
        step_filters=step_filters,
        component=component,
    )
    if waveform.x_unit != "s":
        raise ValueError("THD analysis requires time-domain waveform data.")

    uniform = prepare_period_window(
        waveform.x,
        waveform.y,
        fundamental_hz=fundamental_hz,
        periods=periods,
        t_end=t_end,
        samples_per_cycle=samples_per_cycle,
    )
    spectrum = compute_single_sided_fft(uniform, remove_mean=True)
    fundamental_index = periods
    if fundamental_index >= spectrum.amplitude.shape[0]:
        raise ValueError("The selected waveform window does not contain the requested fundamental.")

    fundamental_amplitude = float(spectrum.amplitude[fundamental_index])
    if fundamental_amplitude <= 0:
        raise ValueError(
            "The requested fundamental has zero amplitude in the selected waveform window."
        )
    fundamental_rms = float(fundamental_amplitude / sqrt(2.0))

    harmonic_rms_sum = 0.0
    contributions: list[ThdHarmonic] = []
    for harmonic in range(1, harmonics + 1):
        index = harmonic * periods
        if index >= spectrum.amplitude.shape[0]:
            break
        amplitude = float(spectrum.amplitude[index])
        rms = float(amplitude / sqrt(2.0))
        percent = 100.0 * amplitude / fundamental_amplitude if fundamental_amplitude else 0.0
        if harmonic > 1:
            harmonic_rms_sum += rms * rms
        contributions.append(
            ThdHarmonic(
                harmonic=harmonic,
                frequency_hz=float(harmonic * fundamental_hz),
                amplitude=amplitude,
                rms=rms,
                percent_of_fundamental=float(percent),
            )
        )

    thd_ratio = float(sqrt(harmonic_rms_sum) / fundamental_rms)
    return ThdAnalysis(
        raw_path=waveform.raw_path,
        plot_name=waveform.plot_name,
        signal=waveform.signal,
        step=waveform.step,
        component=waveform.component,
        sample_count=uniform.sample_count,
        window_start_s=uniform.window_start_s,
        window_end_s=uniform.window_end_s,
        fundamental_hz=float(fundamental_hz),
        harmonics=harmonics,
        fundamental_amplitude=fundamental_amplitude,
        fundamental_rms=fundamental_rms,
        thd_ratio=thd_ratio,
        thd_percent=float(thd_ratio * 100.0),
        contributions=tuple(contributions),
    )


__all__ = ["SERVICE_SPEC", "ThdAnalysis", "ThdHarmonic", "compute_thd"]
