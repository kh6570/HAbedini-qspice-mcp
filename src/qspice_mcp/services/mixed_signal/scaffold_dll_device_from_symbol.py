"""Generate a `.DLL` source scaffold from an existing schematic symbol."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.services._backends.schematic_editor import (
    open_schematic_editor,
    read_component_symbol_metadata,
)
from qspice_mcp.services._internals.dll_contracts import (
    DllSymbolContract,
    build_dll_symbol_contract,
    normalize_dll_identifier,
)
from qspice_mcp.services._shared.paths import resolve_workspace_output_path
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings  # noqa: F401

_DLL_FROM_SYMBOL_TEMPLATE = r"""// QSPICE custom device DLL scaffold
// derived from {reference} in {schematic_name}
// Device name: {device_name}
// Exported entry point: {export_name}
// Build: cl /LD /EHsc {safe_name}.cpp /Fe{device_name}.dll
//        or use the CMakeLists.txt generated alongside this file.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cmath>

union uData
{{
    bool b;
    char c;
    unsigned char uc;
    short s;
    unsigned short us;
    int i;
    unsigned int ui;
    float f;
    double d;
    long long int i64;
    unsigned long long int ui64;
    char *str;
    unsigned char *bytes;
}};

int __stdcall DllMain(void *module, unsigned int reason, void *reserved) {{
    (void)module;
    (void)reason;
    (void)reserved;
    return 1;
}}

{undef_lines}

extern "C" __declspec(dllexport) void {export_name}(
    void **opaque,
    double t,
    union uData *data
)
{{
    (void)opaque;
    (void)t;
{pin_bindings}

    // TODO: implement device behaviour here.
    // Avoid shared global mutable state when multiple schematic instances use the same DLL.
{output_initializers}
}}
"""

_DLL_FROM_SYMBOL_CMAKE_TEMPLATE = r"""# CMakeLists.txt for {device_name} QSPICE custom device DLL
cmake_minimum_required(VERSION 3.16)
project({safe_name} LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library({safe_name} SHARED {safe_name}.cpp)

if(WIN32)
    target_compile_definitions({safe_name} PRIVATE WIN32_LEAN_AND_MEAN)
    set_target_properties({safe_name} PROPERTIES
        PREFIX ""
        SUFFIX ".dll"
        OUTPUT_NAME "{device_name}"
    )
endif()

# Place the compiled DLL where QSPICE can find it, then point the schematic
# block value at {device_name}.
"""


@dataclass(frozen=True, slots=True)
class DllDeviceSymbolScaffold:
    """Metadata for one symbol-driven `.DLL` scaffold."""

    schematic_path: Path
    reference: str
    device_name: str
    export_name: str
    input_pin_names: tuple[str, ...]
    output_pin_names: tuple[str, ...]
    source_path: Path
    cmake_path: Path
    source_line_count: int
    cmake_line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_dll_device_from_symbol",
    title="Scaffold DLL Device From Symbol",
    summary=(
        "Generate a C++ DLL custom-device scaffold directly from one existing `.DLL` "
        "schematic block so the source stub matches the symbol contract."
    ),
    phase="implemented",
)


def _render_pin_bindings(symbol_contract: DllSymbolContract) -> str:
    lines = []
    for pin in symbol_contract.pins:
        if pin.direction == "input":
            lines.append(f"    double {pin.name} = data[{pin.data_index}].d; // input")
        else:
            lines.append(f"    double &{pin.name} = data[{pin.data_index}].d; // output")
    return "\n".join(lines)


def _render_output_initializers(symbol_contract: DllSymbolContract) -> str:
    outputs = [pin.name for pin in symbol_contract.pins if pin.direction == "output"]
    if not outputs:
        return "    // No output pins are currently defined on this symbol."
    return "\n".join(f"    {pin_name} = 0.0;" for pin_name in outputs)


def scaffold_dll_device_from_symbol(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    settings: object,
    reference: str,
    output_dir: str | None = None,
) -> DllDeviceSymbolScaffold:
    """Generate one `.DLL` source scaffold from an existing schematic symbol."""

    del settings
    editor, resolved_schematic_path, _ = open_schematic_editor(
        schematic_path,
        workspace_root=workspace_root.resolve(strict=False),
    )
    symbol_metadata = read_component_symbol_metadata(editor, reference=reference)
    symbol_contract = build_dll_symbol_contract(
        reference=reference,
        device_name=str(editor.get_component_value(reference)),
        metadata=symbol_metadata,
    )

    safe_name = normalize_dll_identifier(symbol_contract.device_name)
    export_name = safe_name
    dir_path = (
        Path(output_dir).resolve(strict=False)
        if output_dir is not None
        else resolved_schematic_path.parent
    )
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

    source_content = _DLL_FROM_SYMBOL_TEMPLATE.format(
        reference=reference,
        schematic_name=resolved_schematic_path.name,
        device_name=symbol_contract.device_name,
        export_name=export_name,
        safe_name=safe_name,
        undef_lines="\n".join(f"#undef {pin.name}" for pin in symbol_contract.pins),
        pin_bindings=_render_pin_bindings(symbol_contract),
        output_initializers=_render_output_initializers(symbol_contract),
    )
    cmake_content = _DLL_FROM_SYMBOL_CMAKE_TEMPLATE.format(
        device_name=symbol_contract.device_name,
        safe_name=safe_name,
    )

    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(source_content, encoding="utf-8")
    cmake_path.write_text(cmake_content, encoding="utf-8")

    return DllDeviceSymbolScaffold(
        schematic_path=resolved_schematic_path,
        reference=reference,
        device_name=symbol_contract.device_name,
        export_name=export_name,
        input_pin_names=symbol_contract.input_pin_names,
        output_pin_names=symbol_contract.output_pin_names,
        source_path=source_path,
        cmake_path=cmake_path,
        source_line_count=len(source_content.splitlines()),
        cmake_line_count=len(cmake_content.splitlines()),
        notes=(
            f"Derived from {reference} in {resolved_schematic_path.name}.",
            f"Build with: cl /LD /EHsc {safe_name}.cpp /Fe{symbol_contract.device_name}.dll",
            "Avoid shared global mutable state when multiple instances use the same DLL.",
        ),
    )


__all__ = [
    "SERVICE_SPEC",
    "DllDeviceSymbolScaffold",
    "scaffold_dll_device_from_symbol",
]
