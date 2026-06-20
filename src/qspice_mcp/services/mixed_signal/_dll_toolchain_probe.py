"""Probe QSpice-bundled DMC, MSVC, and CMake availability for DLL builds."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from qspice_mcp.adapters.probe import discover_executable
from qspice_mcp.infra.subprocess import run_subprocess


@dataclass(frozen=True, slots=True)
class DllBuildToolchainSnapshot:
    """Runtime snapshot of optional DLL build toolchains."""

    dmc_available: bool
    dmc_path: Path | None
    msvc_available: bool
    msvc_cl_on_path: bool
    vcvars64_bat: Path | None
    cmake_available: bool
    auto_toolchain: str | None
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "dmc_available": self.dmc_available,
            "dmc_path": str(self.dmc_path) if self.dmc_path is not None else None,
            "msvc_available": self.msvc_available,
            "msvc_cl_on_path": self.msvc_cl_on_path,
            "vcvars64_bat": str(self.vcvars64_bat) if self.vcvars64_bat is not None else None,
            "cmake_available": self.cmake_available,
            "auto_toolchain": self.auto_toolchain,
            "notes": list(self.notes),
        }


def resolve_qspice_executable(qspice_executable: Path | None) -> Path | None:
    if qspice_executable is not None and qspice_executable.is_file():
        return qspice_executable.resolve(strict=False)
    discovered, _source = discover_executable(None)
    if discovered is not None and discovered.is_file():
        return discovered.resolve(strict=False)
    return None


def find_bundled_dmc(qspice_executable: Path | None) -> Path | None:
    resolved = resolve_qspice_executable(qspice_executable)
    if resolved is None:
        return None
    candidate = resolved.parent / "dm" / "bin" / "dmc.exe"
    if candidate.is_file():
        return candidate.resolve(strict=False)
    return None


def find_vcvars64_bat() -> Path | None:
    """Locate MSVC environment bootstrap script on Windows when ``cl`` is not on PATH."""

    if sys.platform != "win32":
        return None

    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if vswhere.is_file():
        probe = run_subprocess(
            (
                str(vswhere),
                "-latest",
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ),
            cwd=Path.cwd(),
            timeout_s=30.0,
        )
        install_root = probe.stdout.strip()
        if probe.exit_code == 0 and install_root:
            vcvars = Path(install_root) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
            if vcvars.is_file():
                return vcvars

    for edition in ("Community", "Professional", "Enterprise", "BuildTools"):
        for year in ("2022", "2019"):
            vcvars = (
                Path(rf"C:\Program Files\Microsoft Visual Studio\{year}\{edition}")
                / "VC"
                / "Auxiliary"
                / "Build"
                / "vcvars64.bat"
            )
            if vcvars.is_file():
                return vcvars
    return None


def _resolve_auto_toolchain(
    *,
    bundled_dmc: Path | None,
    msvc_available: bool,
    cmake_available: bool,
) -> str | None:
    if bundled_dmc is not None:
        return "dmc"
    if msvc_available:
        return "msvc"
    if cmake_available:
        return "cmake"
    return None


def _dll_toolchain_notes(
    *,
    bundled_dmc: Path | None,
    qspice_executable: Path | None,
    cl_on_path: bool,
    msvc_available: bool,
    cmake_available: bool,
    auto_toolchain: str | None,
) -> tuple[str, ...]:
    notes: list[str] = []
    if bundled_dmc is not None:
        notes.append(f"QSpice-bundled DMC is available at {bundled_dmc}.")
    elif resolve_qspice_executable(qspice_executable) is None:
        notes.append(
            "Bundled DMC was not found because QSPICE_EXE is unset or invalid "
            "(expected <install>/dm/bin/dmc.exe beside QSPICE64.exe)."
        )
    else:
        notes.append(
            "QSpice is configured but bundled DMC was not found beside the executable."
        )

    if msvc_available:
        if cl_on_path:
            notes.append("MSVC `cl` is available on PATH.")
        else:
            notes.append(
                "MSVC `cl` is not on PATH, but vcvars64.bat was discovered for bootstrap."
            )
    else:
        notes.append(
            "MSVC is unavailable: `cl` is not on PATH and no vcvars64.bat was discovered."
        )

    if cmake_available:
        notes.append("CMake is available on PATH.")
    else:
        notes.append("CMake is not on PATH.")

    if auto_toolchain is None:
        notes.append(
            "No DLL build toolchain is ready for toolchain='auto'. "
            "Configure QSPICE_EXE for bundled DMC, install MSVC build tools, "
            "or add CMake to PATH."
        )
    elif auto_toolchain == "msvc" and not cl_on_path:
        notes.append(
            "IDE-spawned MCP sessions often lack `cl` on PATH; build_dll_device "
            "will bootstrap MSVC via vcvars64.bat when selected."
        )
    return tuple(notes)


def describe_dll_build_toolchain(
    *,
    qspice_executable: Path | None = None,
) -> DllBuildToolchainSnapshot:
    """Report DLL build toolchain availability separate from simulator configuration."""

    bundled_dmc = find_bundled_dmc(qspice_executable)
    cl_on_path = which("cl") is not None
    vcvars = find_vcvars64_bat()
    msvc_available = cl_on_path or vcvars is not None
    cmake_available = which("cmake") is not None

    auto_toolchain = _resolve_auto_toolchain(
        bundled_dmc=bundled_dmc,
        msvc_available=msvc_available,
        cmake_available=cmake_available,
    )
    notes = _dll_toolchain_notes(
        bundled_dmc=bundled_dmc,
        qspice_executable=qspice_executable,
        cl_on_path=cl_on_path,
        msvc_available=msvc_available,
        cmake_available=cmake_available,
        auto_toolchain=auto_toolchain,
    )

    return DllBuildToolchainSnapshot(
        dmc_available=bundled_dmc is not None,
        dmc_path=bundled_dmc,
        msvc_available=msvc_available,
        msvc_cl_on_path=cl_on_path,
        vcvars64_bat=vcvars,
        cmake_available=cmake_available,
        auto_toolchain=auto_toolchain,
        notes=tuple(notes),
    )


def dll_build_degradation_hints(
    *,
    qspice_executable: Path | None = None,
    error: str | None = None,
) -> dict[str, object]:
    """Return MCP-friendly toolchain hints when auto DLL build is skipped or fails."""

    snapshot = describe_dll_build_toolchain(qspice_executable=qspice_executable)
    suggestions: list[str] = []
    if not snapshot.dmc_available:
        suggestions.append(
            "Set QSPICE_EXE to a valid QSPICE64.exe install so bundled DMC can be discovered."
        )
    if snapshot.msvc_available and not snapshot.msvc_cl_on_path:
        suggestions.append(
            "MSVC is installed but `cl` is not on PATH in this MCP session; "
            "build_dll_device can bootstrap via vcvars64.bat when toolchain='msvc' or 'auto'."
        )
    elif not snapshot.msvc_available:
        suggestions.append(
            "Install Visual Studio Build Tools or run from a Developer Command Prompt "
            "for toolchain='msvc'."
        )
    if not snapshot.cmake_available:
        suggestions.append(
            "Add CMake to PATH when a CMakeLists.txt is present beside the C-block source."
        )
    if snapshot.auto_toolchain is None:
        suggestions.append(
            "Call describe_server_capabilities and inspect optional_backends.dll_build_toolchain "
            "before relying on write_workspace_text_file auto-build."
        )
    elif error is not None and "after trying" in error:
        suggestions.append(
            "Auto-build already retried alternate toolchains (DMC → MSVC → CMake). "
            "Fix compiler errors in the source or pass an explicit dll_toolchain."
        )

    payload = snapshot.as_dict()
    payload["recovery_suggestions"] = suggestions
    if error is not None:
        payload["error"] = error
    return payload


__all__ = [
    "DllBuildToolchainSnapshot",
    "describe_dll_build_toolchain",
    "dll_build_degradation_hints",
    "find_bundled_dmc",
    "find_vcvars64_bat",
    "resolve_qspice_executable",
]
