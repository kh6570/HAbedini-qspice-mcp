"""Compile a workspace C-block source file into a QSpice custom-device DLL."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from shutil import which
from typing import Literal

from qspice_mcp.core.exceptions import BackendUnavailableError, ValidationError
from qspice_mcp.infra.subprocess import SubprocessResult, run_subprocess
from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
    validate_existing_file,
)
from qspice_mcp.services.mixed_signal._dll_toolchain_probe import (
    find_bundled_dmc,
    find_vcvars64_bat,
)
from qspice_mcp.services.service_spec import ServiceSpec

Toolchain = Literal["auto", "dmc", "msvc", "cmake"]


@dataclass(frozen=True, slots=True)
class BuiltDllDevice:
    """Metadata for one compiled custom-device DLL."""

    source_path: Path
    output_path: Path
    toolchain: str
    command: tuple[str, ...]
    exit_code: int
    duration_s: float
    stdout: str
    stderr: str


_CMD_SHELL_PREFIX_LENGTH = 3

SERVICE_SPEC = ServiceSpec(
    name="build_dll_device",
    title="Build DLL Device",
    summary=(
        "Compile a workspace C or C++ source file into a `.dll` custom device "
        "using QSpice-bundled DMC, MSVC (`cl`), or CMake when available."
    ),
    phase="implemented",
    read_only=False,
)


def _resolve_output_path(
    source_path: Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None,
) -> Path:
    default_output = source_path.with_suffix(".dll")
    if output_path is None:
        return default_output.resolve(strict=False)
    return resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=default_output,
        suffixes=(".dll",),
    )


def _dmc_bin_dir(dmc_exe: Path) -> Path:
    return dmc_exe.parent.resolve(strict=False)


def _dmc_command(dmc_exe: Path, source_path: Path) -> tuple[str, ...]:
    return (
        str(dmc_exe),
        "-mn",
        "-WD",
        source_path.name,
        "kernel32.lib",
    )


def _dmc_subprocess_env(dmc_exe: Path) -> dict[str, str]:
    dm_bin = str(_dmc_bin_dir(dmc_exe))
    path_sep = ";" if sys.platform == "win32" else ":"
    existing = os.environ.get("PATH", "")
    env = os.environ.copy()
    env["PATH"] = f"{dm_bin}{path_sep}{existing}" if existing else dm_bin
    return env


def _msvc_command(source_path: Path, output_path: Path) -> tuple[str, ...]:
    return (
        "cl",
        "/LD",
        "/EHsc",
        str(source_path.name),
        f"/Fe{output_path.name}",
    )


def _wrap_msvc_with_vcvars(
    command: tuple[str, ...],
    vcvars: Path,
) -> tuple[str, ...]:
    joined = " ".join(command)
    return ("cmd", "/c", f'call "{vcvars}" && {joined}')


def _cmake_build_dir(source_parent: Path) -> Path:
    return source_parent / "build"


def _cmake_command(source_path: Path) -> tuple[str, ...] | None:
    cmake_lists = source_path.parent / "CMakeLists.txt"
    if not cmake_lists.is_file():
        return None
    build_dir = _cmake_build_dir(source_path.parent)
    return (
        "cmake",
        "-S",
        str(source_path.parent),
        "-B",
        str(build_dir),
        "&&",
        "cmake",
        "--build",
        str(build_dir),
        "--config",
        "Release",
    )


def _select_toolchain(
    *,
    requested: Toolchain,
    source_path: Path,
    qspice_executable: Path | None,
) -> tuple[str, tuple[str, ...], Path | None]:
    """Return selected toolchain name, command, and optional DMC executable path."""

    cl_path = which("cl")
    cmake_path = which("cmake")
    bundled_dmc = find_bundled_dmc(qspice_executable)

    if requested == "dmc":
        if bundled_dmc is None:
            raise BackendUnavailableError(
                "QSpice-bundled DMC was not found. Set QSPICE_EXE to a valid "
                "QSPICE64.exe install path (expected <install>/dm/bin/dmc.exe) "
                "or pass toolchain='msvc' or 'cmake'."
            )
        return "dmc", _dmc_command(bundled_dmc, source_path), bundled_dmc

    if requested == "msvc":
        if cl_path is None and find_vcvars64_bat() is None:
            raise BackendUnavailableError(
                "MSVC `cl` was not found on PATH and no Visual Studio vcvars64.bat "
                "was discovered. Install MSVC build tools or pass toolchain='cmake' "
                "when CMakeLists.txt is present."
            )
        output_path = source_path.with_suffix(".dll")
        return "msvc", _msvc_command(source_path, output_path), None

    if requested == "cmake":
        if cmake_path is None:
            raise BackendUnavailableError("CMake was not found on PATH.")
        command = _cmake_command(source_path)
        if command is None:
            raise ValidationError(
                f"CMake build requested but no CMakeLists.txt found beside {source_path}"
            )
        return "cmake", command, None

    if bundled_dmc is not None:
        return "dmc", _dmc_command(bundled_dmc, source_path), bundled_dmc

    if cl_path is not None or find_vcvars64_bat() is not None:
        output_path = source_path.with_suffix(".dll")
        return "msvc", _msvc_command(source_path, output_path), None

    if cmake_path is not None:
        command = _cmake_command(source_path)
        if command is not None:
            return "cmake", command, None

    raise BackendUnavailableError(
        "No supported DLL build toolchain found. Configure QSPICE_EXE for bundled DMC, "
        "install MSVC (`cl`), add CMake, or run from a Developer Command Prompt."
    )


def _run_build_command(
    command: tuple[str, ...],
    *,
    working_directory: Path,
    timeout_s: float | None,
    env: dict[str, str] | None = None,
) -> SubprocessResult:
    if len(command) >= _CMD_SHELL_PREFIX_LENGTH and command[0] == "cmd" and command[1] == "/c":
        return run_subprocess(command, cwd=working_directory, timeout_s=timeout_s, env=env)
    if "&&" in command:
        joined = " ".join(command)
        return run_subprocess(
            ("cmd", "/c", joined),
            cwd=working_directory,
            timeout_s=timeout_s,
            env=env,
        )
    return run_subprocess(command, cwd=working_directory, timeout_s=timeout_s, env=env)


def build_dll_device(
    source_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    toolchain: Toolchain = "auto",
    timeout_s: float | None = 120.0,
    qspice_executable: Path | None = None,
) -> BuiltDllDevice:
    """Compile one workspace `.cpp` file into a `.dll` beside or at output_path."""

    resolved_source = validate_existing_file(
        source_path,
        workspace_root=workspace_root,
        suffixes=(".cpp", ".c", ".cc", ".cxx"),
    )
    resolved_output = _resolve_output_path(
        resolved_source,
        workspace_root=workspace_root,
        output_path=output_path,
    )

    selected_toolchain, command, bundled_dmc = _select_toolchain(
        requested=toolchain,
        source_path=resolved_source,
        qspice_executable=qspice_executable,
    )
    subprocess_env: dict[str, str] | None = None
    if selected_toolchain == "msvc":
        command = _msvc_command(resolved_source, resolved_output)
        if which("cl") is None:
            vcvars = find_vcvars64_bat()
            if vcvars is not None:
                command = _wrap_msvc_with_vcvars(command, vcvars)
    elif selected_toolchain == "dmc" and bundled_dmc is not None:
        command = _dmc_command(bundled_dmc, resolved_source)
        subprocess_env = _dmc_subprocess_env(bundled_dmc)

    process = _run_build_command(
        command,
        working_directory=resolved_source.parent,
        timeout_s=timeout_s,
        env=subprocess_env,
    )

    if process.exit_code != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "compiler failed"
        raise ValidationError(f"DLL build failed with exit code {process.exit_code}: {detail}")

    if not resolved_output.is_file():
        sibling = resolved_source.with_suffix(".dll")
        if sibling.is_file() and sibling != resolved_output:
            sibling.replace(resolved_output)
        elif not resolved_output.is_file():
            raise ValidationError(
                f"DLL build reported success but output file was not created: {resolved_output}"
            )

    return BuiltDllDevice(
        source_path=resolved_source,
        output_path=resolved_output,
        toolchain=selected_toolchain,
        command=command,
        exit_code=process.exit_code,
        duration_s=process.duration_s,
        stdout=process.stdout,
        stderr=process.stderr,
    )


__all__ = ["SERVICE_SPEC", "BuiltDllDevice", "Toolchain", "build_dll_device"]
