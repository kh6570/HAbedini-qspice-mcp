"""Service for read-only ERC-style checks on a netlist artifact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.schematic._erc import evaluate_netlist
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.services.schematic._erc import ErcFinding


@dataclass(frozen=True, slots=True)
class NetlistCheckReport:
    """ERC findings for one netlist."""

    netlist_path: Path
    ok: bool
    error_count: int
    warning_count: int
    info_count: int
    findings: tuple[ErcFinding, ...]


SERVICE_SPEC = ServiceSpec(
    name="check_netlist",
    title="Check Netlist",
    summary="Run read-only ERC-style checks on a `.net`/`.cir` netlist.",
    phase="implemented",
    read_only=True,
)


def check_netlist(
    netlist_path: str | Path,
    *,
    workspace_root: Path,
) -> NetlistCheckReport:
    """Return ERC findings for one netlist artifact."""

    resolved_path = validate_existing_file(
        netlist_path,
        workspace_root=workspace_root.resolve(strict=False),
        suffixes=(".net", ".cir"),
    )
    report = evaluate_netlist(resolved_path.read_text(encoding="utf-8", errors="replace"))
    return NetlistCheckReport(
        netlist_path=resolved_path,
        ok=report.ok,
        error_count=report.error_count,
        warning_count=report.warning_count,
        info_count=report.info_count,
        findings=report.findings,
    )


__all__ = ["SERVICE_SPEC", "NetlistCheckReport", "check_netlist"]
