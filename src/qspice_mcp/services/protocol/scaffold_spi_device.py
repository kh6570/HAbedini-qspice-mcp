"""Scaffold an SPI bus device DLL project for QSpice co-simulation."""

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


_SPI_TEMPLATE = r"""// QSpice SPI custom device: {device_name}
// Build: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll
// See QSpice Help > Digital/Custom Devices > SPI Bus Helpers.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cmath>

// ---------------------------------------------------------------------------
// QSpice SPI helper declarations (imported from the simulator at runtime).
// ---------------------------------------------------------------------------
// These functions are provided by QSpice and resolve automatically when
// the DLL is loaded by the simulator.  They are NOT exported from the DLL.

// SPI helpers:
//   double qspice_spi_write(double mosi, double miso, double sclk, double cs,
//                           double data, double clk_period, int mode, int bits)
//   double qspice_spi_read(double mosi, double miso, double sclk, double cs,
//                          double clk_period, int mode, int bits)
//   mode: 0=CPOL=0,CPHA=0  1=CPOL=0,CPHA=1  2=CPOL=1,CPHA=0  3=CPOL=1,CPHA=1

extern "C" {{
    double qspice_spi_write(
        double mosi, double miso, double sclk, double cs,
        double data, double clk_period, int mode, int bits
    );
    double qspice_spi_read(
        double mosi, double miso, double sclk, double cs,
        double clk_period, int mode, int bits
    );
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

    // pins[0] = MOSI net voltage
    // pins[1] = MISO net voltage
    // pins[2] = SCLK net voltage
    // pins[3] = CS net voltage
    // pins[4] = ... additional device pins
    double mosi = (pin_count > 0) ? pins[0] : 0.0;
    double miso = (pin_count > 1) ? pins[1] : 0.0;
    double sclk = (pin_count > 2) ? pins[2] : 0.0;
    double cs   = (pin_count > 3) ? pins[3] : 0.0;

    // TODO: implement your SPI device behaviour here.
    // Example: read one byte in SPI mode 0.
    // double rx_data = qspice_spi_read(mosi, miso, sclk, cs, 1e-6, 0, 8);

    (void)mosi;
    (void)miso;
    (void)sclk;
    (void)cs;
    return 0;
}}

__declspec(dllexport) void __stdcall dll_device_end() {{
    // cleanup if needed
}}

}}  // extern "C"
"""


@dataclass(frozen=True, slots=True)
class SpiDeviceScaffold:
    """Metadata for one scaffolded SPI bus-device DLL project."""

    device_name: str
    source_path: Path
    line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_spi_device",
    title="Scaffold SPI Device",
    summary=(
        "Generate a C++ DLL scaffold that uses QSpice's built-in SPI bus "
        "helper functions (qspice_spi_read, qspice_spi_write) for "
        "protocol-level co-simulation with configurable SPI mode."
    ),
    phase="implemented",
)


def scaffold_spi_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: object,
    output_path: str | None = None,
) -> SpiDeviceScaffold:
    """Generate an SPI bus-device C++ DLL scaffold."""

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

    content = _SPI_TEMPLATE.format(device_name=device_name, safe_name=safe_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return SpiDeviceScaffold(
        device_name=device_name,
        source_path=resolved,
        line_count=len(content.splitlines()),
        notes=(
            f"Build with: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll",
            f"Place {device_name}.dll where QSpice can find it.",
            "Add an SPI bus symbol and a DLL Device symbol to your schematic.",
            "SPI mode is selected per-call (0-3) via the mode parameter.",
        ),
    )


__all__ = ["SERVICE_SPEC", "SpiDeviceScaffold", "scaffold_spi_device"]
