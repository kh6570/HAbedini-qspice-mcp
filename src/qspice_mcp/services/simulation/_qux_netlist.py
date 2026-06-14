"""QUX companion netlist generation for DLL-bearing schematics."""

from __future__ import annotations

from shutil import copy2
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ArtifactMissingError
from qspice_mcp.services._internals.qux import (
    build_qux_netlist_command,
    discover_qux_netlist_output,
    resolve_qux_companion,
    run_qux_command,
)
from qspice_mcp.services.simulation._netlist_result import GeneratedNetlist

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


def generate_netlist_with_qux(
    schematic_path: Path,
    destination: Path,
    *,
    settings: QSpiceSettings,
) -> GeneratedNetlist:
    """Generate a derived netlist through the documented QUX `-Netlist` path."""

    companion = resolve_qux_companion(settings)
    command = build_qux_netlist_command(companion.qux_path, schematic_path)
    run_qux_command(command, cwd=schematic_path.parent.resolve(strict=False))

    qux_output = discover_qux_netlist_output(schematic_path)
    if qux_output is None:
        raise ArtifactMissingError(
            "QUX.exe -Netlist completed without creating a sibling .cir or .net artifact "
            f"for {schematic_path.name}."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    copied = False
    if qux_output.resolve(strict=False) != destination.resolve(strict=False):
        copy2(qux_output, destination)
        copied = True

    return GeneratedNetlist(
        source_path=schematic_path,
        netlist_path=destination.resolve(strict=False),
        source_kind="schematic",
        refreshed=True,
        copied=copied,
        netlist_backend="qux",
        warnings=(
            "Generated a derived netlist from the schematic via companion QUX.exe -Netlist.",
        ),
    )


__all__ = ["generate_netlist_with_qux"]
