"""Service for describing companion QUX export support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.adapters.probe import probe_qspice
from qspice_mcp.services._internals.qux import (
    COMPANION_NAME,
    SCHEMATIC_INPUT_SUFFIXES,
    SUPPORTED_EXPORT_FORMATS,
    SUPPORTED_SWITCHES,
    WAVEFORM_INPUT_SUFFIXES,
    resolve_qux_companion,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


@dataclass(frozen=True, slots=True)
class QuxExportSupport:
    """Reported companion-export capability for the current QSpice install."""

    available: bool
    qspice_executable: Path | None
    qux_path: Path | None
    supports_export: bool
    supports_netlist: bool
    supports_dll_variables: bool
    supported_switches: tuple[str, ...]
    supported_export_formats: tuple[str, ...]
    waveform_input_suffixes: tuple[str, ...]
    schematic_input_suffixes: tuple[str, ...]
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="describe_qux_export_support",
    title="Describe QUX Export Support",
    summary=(
        "Describe whether the companion QUX executable is available and which "
        "documented exports it supports."
    ),
    phase="implemented",
)


def describe_qux_export_support(*, settings: QSpiceSettings) -> QuxExportSupport:
    """Describe the documented QUX companion-export surface for the current install."""

    effective_settings = settings.normalized()
    probe = probe_qspice(effective_settings)
    qspice_executable = (
        probe.executable.resolve(strict=False) if probe.executable is not None else None
    )

    if qspice_executable is None or not probe.exists:
        return QuxExportSupport(
            available=False,
            qspice_executable=qspice_executable,
            qux_path=None,
            supports_export=False,
            supports_netlist=False,
            supports_dll_variables=False,
            supported_switches=SUPPORTED_SWITCHES,
            supported_export_formats=tuple(fmt.upper() for fmt in SUPPORTED_EXPORT_FORMATS),
            waveform_input_suffixes=WAVEFORM_INPUT_SUFFIXES,
            schematic_input_suffixes=SCHEMATIC_INPUT_SUFFIXES,
            notes=(
                "QSpice executable is not configured or discoverable, so companion "
                "QUX support cannot be confirmed.",
            ),
        )

    expected_qux_path = qspice_executable.with_name(COMPANION_NAME).resolve(strict=False)
    try:
        companion = resolve_qux_companion(effective_settings)
    except Exception:
        return QuxExportSupport(
            available=False,
            qspice_executable=qspice_executable,
            qux_path=expected_qux_path,
            supports_export=False,
            supports_netlist=False,
            supports_dll_variables=False,
            supported_switches=SUPPORTED_SWITCHES,
            supported_export_formats=tuple(fmt.upper() for fmt in SUPPORTED_EXPORT_FORMATS),
            waveform_input_suffixes=WAVEFORM_INPUT_SUFFIXES,
            schematic_input_suffixes=SCHEMATIC_INPUT_SUFFIXES,
            notes=("QSpice is available, but companion QUX.exe was not found next to it.",),
        )

    return QuxExportSupport(
        available=True,
        qspice_executable=companion.qspice_executable,
        qux_path=companion.qux_path,
        supports_export=True,
        supports_netlist=True,
        supports_dll_variables=True,
        supported_switches=SUPPORTED_SWITCHES,
        supported_export_formats=tuple(fmt.upper() for fmt in SUPPORTED_EXPORT_FORMATS),
        waveform_input_suffixes=WAVEFORM_INPUT_SUFFIXES,
        schematic_input_suffixes=SCHEMATIC_INPUT_SUFFIXES,
        notes=(
            "Support is derived from the documented companion QUX.exe switches "
            "and the local executable layout.",
        ),
    )


__all__ = ["SERVICE_SPEC", "QuxExportSupport", "describe_qux_export_support"]
