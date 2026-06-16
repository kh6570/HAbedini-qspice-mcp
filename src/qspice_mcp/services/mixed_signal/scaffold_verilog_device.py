"""Scaffold a Verilog custom-device module for QSpice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

_VERILOG_TEMPLATE = r"""// QSpice Verilog custom device: {device_name}
// See QSpice Help > Digital/Custom Devices > Verilog Devices.

`timescale 1ns / 1ps

module {module_name} (
    // QSpice maps Verilog ports to symbol pins by position.
    // Port directions are inferred from QSpice symbol pin types.
    input  wire a,     // example input pin
    output wire y      // example output pin
);

    // -----------------------------------------------------------------------
    // Behavioural description
    // -----------------------------------------------------------------------

    // Simple combinatorial example: replace with your logic.
    assign y = a;

endmodule
"""


@dataclass(frozen=True, slots=True)
class VerilogDeviceScaffold:
    """Metadata for one scaffolded Verilog custom-device module."""

    device_name: str
    output_path: Path
    line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_verilog_device",
    title="Scaffold Verilog Device",
    summary=(
        "Generate a Verilog module scaffold for use as a QSpice custom device "
        "through the documented Verilog device integration path."
    ),
    phase="implemented",
)


def scaffold_verilog_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    output_path: str | None = None,
) -> VerilogDeviceScaffold:
    """Generate a Verilog custom-device module scaffold."""

    del settings
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in device_name)
    if not safe_name or (not safe_name[0].isalpha() and safe_name[0] != "_"):
        raise ValueError(
            "device_name must start with a letter or underscore for a valid Verilog identifier."
        )

    module_name = safe_name.lstrip("_") or safe_name

    resolved = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=workspace_root / f"{module_name}.v",
        suffixes=(".v", ".sv"),
    )

    content = _VERILOG_TEMPLATE.format(device_name=device_name, module_name=module_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return VerilogDeviceScaffold(
        device_name=device_name,
        output_path=resolved,
        line_count=len(content.splitlines()),
        notes=(
            f"Add a 'Verilog Device' symbol to your QSpice schematic and set File={resolved.name}.",
            "Ports in the module declaration are mapped to symbol pins by position.",
        ),
    )


__all__ = ["SERVICE_SPEC", "VerilogDeviceScaffold", "scaffold_verilog_device"]
