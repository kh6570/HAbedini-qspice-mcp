"""Service for read-only ERC-style checks on a supported schematic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic._connectivity import build_connectivity
from qspice_mcp.services.schematic._erc import evaluate_schematic_connectivity
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services.schematic._erc import ErcFinding


@dataclass(frozen=True, slots=True)
class SchematicCheckReport:
    """ERC findings for one schematic."""

    schematic_path: Path
    ok: bool
    error_count: int
    warning_count: int
    info_count: int
    findings: tuple[ErcFinding, ...]


SERVICE_SPEC = ServiceSpec(
    name="check_schematic",
    title="Check Schematic",
    summary="Run read-only ERC-style checks on a supported schematic.",
    phase="implemented",
    read_only=True,
)


def check_schematic(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
) -> SchematicCheckReport:
    """Return ERC findings for one supported clean-room schematic."""

    resolved_path = validate_existing_file(
        schematic_path,
        workspace_root=workspace_root.resolve(strict=False),
        suffixes=(".qsch",),
    )
    model = build_connectivity(resolved_path)
    report = evaluate_schematic_connectivity(model)
    return SchematicCheckReport(
        schematic_path=resolved_path,
        ok=report.ok,
        error_count=report.error_count,
        warning_count=report.warning_count,
        info_count=report.info_count,
        findings=report.findings,
    )


__all__ = ["SERVICE_SPEC", "SchematicCheckReport", "check_schematic"]
