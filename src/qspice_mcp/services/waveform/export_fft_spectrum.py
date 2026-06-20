"""Service for exporting a derived FFT spectrum as CSV."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.waveform import WaveformComponent, load_waveform
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.waveform._spectral import (
    compute_single_sided_fft,
    prepare_uniform_waveform,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class FftSpectrumExport:
    """Metadata for one derived FFT spectrum artifact."""

    raw_path: Path
    output_path: Path
    signal: str
    step: int
    component: str
    sample_count: int
    bin_count: int
    frequency_resolution_hz: float
    window_start_s: float
    window_end_s: float
    max_frequency_hz: float | None


SERVICE_SPEC = ServiceSpec(
    name="export_fft_spectrum",
    title="Export FFT Spectrum",
    summary=(
        "Resample one time-domain waveform window and export its single-sided FFT spectrum as CSV."
    ),
    phase="implemented",
    read_only=False,
    idempotent=True,
)


def _slugify_signal(signal: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", signal).strip("_").lower()
    return slug or "signal"


def _resolve_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    raw_path: Path,
    signal: str,
) -> Path:
    if output_path is None:
        return raw_path.with_name(f"{raw_path.stem}-{_slugify_signal(signal)}-fft.csv").resolve(
            strict=False
        )
    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() != ".csv":
        raise ValueError("FFT spectrum output path must end in .csv")
    return resolved


def export_fft_spectrum(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    signal: str,
    step: int | None = None,
    step_filters: Mapping[str, object] | None = None,
    component: WaveformComponent = "auto",
    t_start: float | None = None,
    t_end: float | None = None,
    sample_count: int = 4096,
    max_frequency_hz: float | None = None,
    output_path: str | Path | None = None,
) -> FftSpectrumExport:
    """Export a derived single-sided FFT spectrum for one waveform window."""

    waveform = load_waveform(
        raw_path,
        workspace_root=workspace_root.resolve(strict=False),
        signal=signal,
        step=step,
        step_filters=step_filters,
        component=component,
        t_start=t_start,
        t_end=t_end,
    )
    if waveform.x_unit != "s":
        raise ValueError("FFT export requires time-domain waveform data.")
    uniform = prepare_uniform_waveform(waveform.x, waveform.y, sample_count=sample_count)
    spectrum = compute_single_sided_fft(uniform)
    frequency = spectrum.frequency_hz
    amplitude = spectrum.amplitude
    magnitude_db = spectrum.magnitude_db
    phase_deg = spectrum.phase_deg
    if max_frequency_hz is not None:
        mask = frequency <= max_frequency_hz
        frequency = frequency[mask]
        amplitude = amplitude[mask]
        magnitude_db = magnitude_db[mask]
        phase_deg = phase_deg[mask]

    destination = _resolve_output_path(
        output_path,
        workspace_root=workspace_root.resolve(strict=False),
        raw_path=waveform.raw_path,
        signal=waveform.signal,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = ["frequency_hz,amplitude,magnitude_db,phase_deg"]
    for index in range(int(frequency.shape[0])):
        lines.append(
            ",".join(
                (
                    f"{float(frequency[index]):.12g}",
                    f"{float(amplitude[index]):.12g}",
                    f"{float(magnitude_db[index]):.12g}",
                    f"{float(phase_deg[index]):.12g}",
                )
            )
        )
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return FftSpectrumExport(
        raw_path=waveform.raw_path,
        output_path=destination,
        signal=waveform.signal,
        step=waveform.step,
        component=waveform.component,
        sample_count=uniform.sample_count,
        bin_count=int(frequency.shape[0]),
        frequency_resolution_hz=float(1.0 / (uniform.sample_interval_s * uniform.sample_count)),
        window_start_s=uniform.window_start_s,
        window_end_s=uniform.window_end_s,
        max_frequency_hz=max_frequency_hz,
    )


__all__ = ["SERVICE_SPEC", "FftSpectrumExport", "export_fft_spectrum"]
