"""Service for QUX-backed CSV waveform export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.artifacts._qux_export import (
    QuxWaveformExport,
    export_waveform_with_qux,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

SERVICE_SPEC = ServiceSpec(
    name="export_waveform_csv",
    title="Export Waveform CSV",
    summary="Export one or more waveform expressions through the documented QUX CSV export path.",
    phase="implemented",
    read_only=False,
)


def export_waveform_csv(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    expressions: tuple[str, ...] | list[str],
    point_count: int | None = None,
    output_path: str | Path | None = None,
) -> QuxWaveformExport:
    """Export one or more waveform expressions through `QUX.exe -Export ... CSV`."""

    return export_waveform_with_qux(
        raw_path,
        workspace_root=workspace_root,
        settings=settings,
        expressions=expressions,
        export_format="csv",
        point_count=point_count,
        output_path=output_path,
    )


__all__ = ["SERVICE_SPEC", "QuxWaveformExport", "export_waveform_csv"]
