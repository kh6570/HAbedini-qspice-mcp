"""Scaffold a C++ DLL custom-device project for QSPICE."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
    resolve_workspace_path,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings  # noqa: F401

_DLL_TEMPLATE = r"""// QSPICE custom device DLL: {device_name}
// Build: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll
//        or use the CMakeLists.txt generated alongside this file.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cmath>

// QSPICE calls these entry points by ordinal.
// See QSPICE Help > Digital/Custom Devices > C++ DLL Devices.

extern "C" {{

// --- Required entry points ---

// Called once at analysis start.
// count  = number of instances of this device in the schematic.
// Return the size (in doubles) of the per-instance state block, or 0.
__declspec(dllexport) int __stdcall dll_device_count(int count) {{
    (void)count;
    return 0;  // no per-instance state needed for a stateless device
}}

// Called at each iteration with the current pin voltages.
// pins[]   = array of pin/node voltages (input).
// state[]  = per-instance state block (size from dll_device_count).
// deriv[]  = derivative storage (output).
// Return a bitmask: 1 = current source on pin 0, 2 = on pin 1, etc.
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
    (void)pins;
    (void)state;
    (void)deriv;
    (void)pin_count;
    // TODO: implement your device behaviour here.
    return 0;
}}

// Optional: called once at the end of the simulation.
__declspec(dllexport) void __stdcall dll_device_end() {{
    // cleanup if needed
}}

}}  // extern "C"
"""

_CMAKE_TEMPLATE = r"""# CMakeLists.txt for {device_name} QSPICE custom device DLL
cmake_minimum_required(VERSION 3.16)
project({device_name} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library({device_name} SHARED {safe_name}.cpp)

if(WIN32)
    target_compile_definitions({device_name} PRIVATE WIN32_LEAN_AND_MEAN)
    set_target_properties({device_name} PROPERTIES
        PREFIX ""
        SUFFIX ".dll"
    )
endif()

# Place the DLL next to the QSPICE executable or in a directory on the
# library search path so QSPICE can load it by name.
"""


@dataclass(frozen=True, slots=True)
class DllDeviceScaffold:
    """Metadata for one scaffolded C++ DLL custom-device project."""

    device_name: str
    source_path: Path
    cmake_path: Path
    source_line_count: int
    cmake_line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_dll_device",
    title="Scaffold DLL Device",
    summary=(
        "Generate a C++ DLL custom-device project scaffold with the documented "
        "QSPICE entry points (dll_device_count, dll_device, dll_device_end)."
    ),
    phase="implemented",
)


def scaffold_dll_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: object,
    output_dir: str | None = None,
    schematic_path: str | Path | None = None,
) -> DllDeviceScaffold:
    """Generate a C++ `.DLL` custom-device project scaffold.

    When *schematic_path* is provided and *output_dir* is not, the generated
    ``.cpp`` and ``CMakeLists.txt`` are placed next to the schematic so that
    QSPICE's "Show Source" command can find them automatically.
    """

    del settings
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in device_name)
    if not safe_name or safe_name[0].isdigit():
        raise ValueError(
            "device_name must start with a letter and contain valid C++ identifier characters."
        )

    if output_dir is not None:
        dir_path = Path(output_dir).resolve(strict=False)
    elif schematic_path is not None:
        resolved_schematic = resolve_workspace_path(schematic_path, workspace_root=workspace_root)
        dir_path = resolved_schematic.parent
    else:
        dir_path = workspace_root.resolve(strict=False) / safe_name

    source_path = resolve_workspace_output_path(
        dir_path / f"{safe_name}.cpp",
        workspace_root=workspace_root,
        default=workspace_root / safe_name / f"{safe_name}.cpp",
        suffixes=(".cpp",),
    )
    cmake_path = resolve_workspace_output_path(
        dir_path / "CMakeLists.txt",
        workspace_root=workspace_root,
        default=workspace_root / safe_name / "CMakeLists.txt",
        suffixes=(".txt",),
    )

    source_content = _DLL_TEMPLATE.format(device_name=device_name, safe_name=safe_name)
    cmake_content = _CMAKE_TEMPLATE.format(device_name=device_name, safe_name=safe_name)

    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source_content, encoding="utf-8")
    cmake_path.write_text(cmake_content, encoding="utf-8")

    return DllDeviceScaffold(
        device_name=device_name,
        source_path=source_path,
        cmake_path=cmake_path,
        source_line_count=len(source_content.splitlines()),
        cmake_line_count=len(cmake_content.splitlines()),
        notes=(
            f"Build with: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll",
            f"Or: cmake -S {safe_name} -B {safe_name}/build && cmake --build {safe_name}/build",
            f"Place {device_name}.dll where QSPICE can find it, then use "
            f"a 'DLL Device' symbol in your schematic with Device={device_name}.",
        ),
    )


__all__ = ["SERVICE_SPEC", "DllDeviceScaffold", "scaffold_dll_device"]
