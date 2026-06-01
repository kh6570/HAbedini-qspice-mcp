"""Service for staging a source with a documented `.bode` directive."""

from __future__ import annotations

from dataclasses import dataclass
from shutil import copy2
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.schematic.add_instruction import (
    add_instruction as add_instruction_service,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

_NETLIST_SUFFIXES = (".net", ".cir")


@dataclass(frozen=True, slots=True)
class PreparedBodeAnalysis:
    """Metadata for one source staged with a `.bode` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_bode_analysis",
    title="Prepare Bode Analysis",
    summary=(
        "Stage a schematic or netlist with a documented `.bode` directive "
        "for closed-loop SMPS analysis."
    ),
    phase="implemented",
    read_only=False,
)


def _resolve_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
    allowed_suffixes: tuple[str, ...],
) -> Path:
    if output_path is None:
        return default.resolve(strict=False)
    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() not in allowed_suffixes:
        rendered_suffixes = ", ".join(allowed_suffixes)
        raise ValueError(f"Output path must end in one of: {rendered_suffixes}")
    return resolved


def _render_bode_instruction(
    perturbation_source: str,
    settling_time: str,
    start_frequency: str,
    stop_frequency: str,
    injection_amplitude: str,
    *,
    square_periods: int | None = None,
    debug: bool = False,
    skip_bias_point: bool = False,
    use_initial_conditions: bool = False,
) -> str:
    tokens = [
        ".bode",
        perturbation_source.strip(),
        settling_time.strip(),
        start_frequency.strip(),
        stop_frequency.strip(),
        injection_amplitude.strip(),
    ]
    if square_periods is not None:
        tokens.append(f"SQUARE={square_periods}")
    if debug:
        tokens.append("DEBUG")
    if skip_bias_point:
        tokens.append("SKIPBP")
    if use_initial_conditions:
        tokens.append("UIC")
    return " ".join(tokens)


def _append_instruction_to_netlist(netlist_path: Path, instruction: str) -> None:
    existing = netlist_path.read_text(encoding="utf-8", errors="replace")
    line_ending = "\r\n" if "\r\n" in existing else "\n"
    lines = existing.replace("\r\n", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    end_index = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip().lower() == ".end":
            end_index = index
            break

    lines.insert(end_index, instruction)
    netlist_path.write_text(f"{line_ending.join(lines)}{line_ending}", encoding="utf-8")


def prepare_bode_analysis(
    source_path: str | Path,
    *,
    workspace_root: Path,
    perturbation_source: str,
    settling_time: str,
    start_frequency: str,
    stop_frequency: str,
    injection_amplitude: str,
    square_periods: int | None = None,
    debug: bool = False,
    skip_bias_point: bool = False,
    use_initial_conditions: bool = False,
    output_path: str | Path | None = None,
) -> PreparedBodeAnalysis:
    """Stage a schematic or netlist with one documented `.bode` directive."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )
    instruction = _render_bode_instruction(
        perturbation_source,
        settling_time,
        start_frequency,
        stop_frequency,
        injection_amplitude,
        square_periods=square_periods,
        debug=debug,
        skip_bias_point=skip_bias_point,
        use_initial_conditions=use_initial_conditions,
    )

    if resolved_source.suffix.lower() == ".qsch":
        destination = _resolve_output_path(
            output_path,
            workspace_root=normalized_workspace,
            default=resolved_source.with_name(f"{resolved_source.stem}-bode.qsch"),
            allowed_suffixes=(".qsch",),
        )
        added = add_instruction_service(
            resolved_source,
            workspace_root=normalized_workspace,
            instruction=instruction,
            output_path=destination,
        )
        return PreparedBodeAnalysis(
            source_path=resolved_source,
            output_path=added.output_path,
            source_kind="schematic",
            instruction=instruction,
            warnings=(
                "Prepared a schematic artifact with one `.bode` directive. "
                "Run simulation on the staged output.",
            ),
        )

    destination = _resolve_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=resolved_source.with_name(f"{resolved_source.stem}-bode{resolved_source.suffix}"),
        allowed_suffixes=_NETLIST_SUFFIXES,
    )
    if destination != resolved_source:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(resolved_source, destination)
    _append_instruction_to_netlist(destination, instruction)
    return PreparedBodeAnalysis(
        source_path=resolved_source,
        output_path=destination,
        source_kind="netlist",
        instruction=instruction,
        warnings=("Prepared a netlist artifact with one inserted `.bode` directive.",),
    )


__all__ = ["SERVICE_SPEC", "PreparedBodeAnalysis", "prepare_bode_analysis"]
