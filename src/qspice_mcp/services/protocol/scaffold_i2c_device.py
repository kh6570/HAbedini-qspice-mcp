"""Scaffold an I2C bus device DLL project for QSpice co-simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings  # noqa: F401


_I2C_TEMPLATE = r"""// QSpice I2C custom device: {device_name}
// Build: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll
// See QSpice Help > Digital/Custom Devices > I2C Bus Helpers.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cmath>

// ---------------------------------------------------------------------------
// QSpice I2C helper declarations (imported from the simulator at runtime).
// ---------------------------------------------------------------------------
// These functions are provided by QSpice and resolve automatically when
// the DLL is loaded by the simulator.  They are NOT exported from the DLL.

// I2C master helpers:
//   double qspice_i2c_write(double sda, double scl, double data, double clk_period)
//   double qspice_i2c_read(double sda, double scl, double clk_period)
//   double qspice_i2c_start(double sda, double scl, double clk_period)
//   double qspice_i2c_stop(double sda, double scl, double clk_period)
//   double qspice_i2c_ack(double sda, double scl, double clk_period)
//   double qspice_i2c_nack(double sda, double scl, double clk_period)

// Declare the helpers as external C symbols so the linker can resolve them.
extern "C" {{
    double qspice_i2c_write(double sda, double scl, double data, double clk_period);
    double qspice_i2c_read(double sda, double scl, double clk_period);
    double qspice_i2c_start(double sda, double scl, double clk_period);
    double qspice_i2c_stop(double sda, double scl, double clk_period);
    double qspice_i2c_ack(double sda, double scl, double clk_period);
    double qspice_i2c_nack(double sda, double scl, double clk_period);
}}

// ---------------------------------------------------------------------------
// Device entry points (called by QSpice).
// ---------------------------------------------------------------------------

extern "C" {{

__declspec(dllexport) int __stdcall dll_device_count(int count) {{
    (void)count;
    return 0;  // stateless device
}}

__declspec(dllexport) int __stdcall dll_device(
    double time,
    double timestep,
    const double *pins,
    double *state,
    double *deriv,
    int pin_count
) {{
    (void)time;
    (void)timestep;
    (void)state;
    (void)deriv;

    // pins[0] = SDA net voltage
    // pins[1] = SCL net voltage
    // pins[2] = ... additional device pins
    double sda = (pin_count > 0) ? pins[0] : 0.0;
    double scl = (pin_count > 1) ? pins[1] : 0.0;

    // TODO: implement your I2C device behaviour here.
    // Example: write one byte (0xAA) when SCL is high.
    // double result = qspice_i2c_write(sda, scl, 0xAA, 1e-6);

    (void)sda;
    (void)scl;
    return 0;
}}

__declspec(dllexport) void __stdcall dll_device_end() {{
    // cleanup if needed
}}

}}  // extern "C"
"""


@dataclass(frozen=True, slots=True)
class I2cDeviceScaffold:
    """Metadata for one scaffolded I2C bus-device DLL project."""

    device_name: str
    source_path: Path
    line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_i2c_device",
    title="Scaffold I2C Device",
    summary=(
        "Generate a C++ DLL scaffold that uses QSpice's built-in I2C bus "
        "helper functions (qspice_i2c_read, qspice_i2c_write, qspice_i2c_start, "
        "qspice_i2c_stop, qspice_i2c_ack, qspice_i2c_nack) for protocol-level "
        "co-simulation."
    ),
    phase="implemented",
)


def scaffold_i2c_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: object,
    output_path: str | None = None,
) -> I2cDeviceScaffold:
    """Generate an I2C bus-device C++ DLL scaffold."""

    del settings
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in device_name)
    if not safe_name or safe_name[0].isdigit():
        raise ValueError(
            "device_name must start with a letter and contain valid C++ identifier characters."
        )

    resolved = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=workspace_root / f"{safe_name}.cpp",
        suffixes=(".cpp",),
    )

    content = _I2C_TEMPLATE.format(device_name=device_name, safe_name=safe_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return I2cDeviceScaffold(
        device_name=device_name,
        source_path=resolved,
        line_count=len(content.splitlines()),
        notes=(
            f"Build with: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll",
            f"Place {device_name}.dll where QSpice can find it.",
            "Add an I2C bus symbol and a DLL Device symbol to your schematic.",
            "The I2C helper functions resolve at runtime when the DLL is loaded.",
        ),
    )


__all__ = ["SERVICE_SPEC", "I2cDeviceScaffold", "scaffold_i2c_device"]
