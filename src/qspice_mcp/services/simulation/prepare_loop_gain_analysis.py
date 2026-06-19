"""Service for staging a source with `.ac` loop-gain analysis guidance."""

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

LoopGainMethod = Literal["tian", "middlebrook"]
_NETLIST_SUFFIXES = (".net", ".cir")
_AC_SWEEP_TYPES = frozenset({"dec", "oct", "lin"})

_METHOD_REFERENCE: dict[LoopGainMethod, str] = {
    "middlebrook": "MiddleBrook.qsch",
    "tian": "Tian.qsch",
}

_METHOD_NOTES: dict[LoopGainMethod, tuple[str, ...]] = {
    "middlebrook": (
        "Middlebrook loop gain uses forward and reverse injection probes around the "
        "feedback break. QSpice ships an example in Examples/MiddleBrook.qsch.",
        "Typical loop-gain expression (after AC simulation with probes on Vin/Vout): "
        "((I(Vout)/I(Vin))*(-V(out)/V(in))-1)/((I(Vout)/I(Vin))+(-V(out)/V(in))+2).",
        "For switched-mode circuits prefer `prepare_bode_analysis` (`.bode`) instead of "
        "small-signal `.ac` loop gain.",
    ),
    "tian": (
        "Tian loop gain uses a single dual-injection probe pair per the Tian method. "
        "QSpice ships an example in Examples/Tian.qsch.",
        "The schematic must include the Tian probe infrastructure before staging; "
        "this tool only adds the `.ac` sweep directive.",
        "For switched-mode circuits prefer `prepare_bode_analysis` (`.bode`) instead of "
        "small-signal `.ac` loop gain.",
    ),
}


@dataclass(frozen=True, slots=True)
class PreparedLoopGainAnalysis:
    """Metadata for one source staged for AC loop-gain analysis."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    method: LoopGainMethod
    instruction: str
    reference_example: str
    method_notes: tuple[str, ...]
    expected_loop_gain_signal: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_loop_gain_analysis",
    title="Prepare Loop Gain Analysis",
    summary=(
        "Stage a schematic or netlist with a documented `.ac` directive and "
        "method-specific loop-gain guidance (Tian or Middlebrook)."
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


def _normalize_method(method: str) -> LoopGainMethod:
    normalized = method.strip().lower()
    if normalized not in _METHOD_REFERENCE:
        allowed = ", ".join(sorted(_METHOD_REFERENCE))
        raise ValueError(f"method must be one of: {allowed}")
    return normalized


def _render_ac_instruction(
    sweep_type: str,
    points: str,
    start: str,
    stop: str,
) -> str:
    normalized_sweep_type = sweep_type.strip().lower()
    if normalized_sweep_type not in _AC_SWEEP_TYPES:
        allowed = ", ".join(sorted(_AC_SWEEP_TYPES))
        raise ValueError(f"sweep_type must be one of: {allowed}")
    return " ".join(
        (
            ".ac",
            normalized_sweep_type,
            points.strip(),
            start.strip(),
            stop.strip(),
        )
    )


def _render_netlist_comment_block(method: LoopGainMethod) -> tuple[str, ...]:
    lines = [f"* loop gain analysis: {method} method"]
    lines.extend(f"* {note}" for note in _METHOD_NOTES[method])
    return tuple(lines)


def _append_instruction_to_netlist(
    netlist_path: Path,
    instruction: str,
    *,
    comment_lines: tuple[str, ...] = (),
) -> None:
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

    insert_block = [*comment_lines, instruction]
    for offset, block_line in enumerate(insert_block):
        lines.insert(end_index + offset, block_line)
    netlist_path.write_text(f"{line_ending.join(lines)}{line_ending}", encoding="utf-8")


def prepare_loop_gain_analysis(
    source_path: str | Path,
    *,
    workspace_root: Path,
    method: str,
    sweep_type: str,
    points: str,
    start: str,
    stop: str,
    expected_loop_gain_signal: str = "OpenLoopGain",
    output_path: str | Path | None = None,
) -> PreparedLoopGainAnalysis:
    """Stage a source with one `.ac` directive and loop-gain method guidance."""

    normalized_method = _normalize_method(method)
    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )
    instruction = _render_ac_instruction(sweep_type, points, start, stop)
    method_notes = _METHOD_NOTES[normalized_method]
    reference_example = _METHOD_REFERENCE[normalized_method]
    normalized_signal = expected_loop_gain_signal.strip() or "OpenLoopGain"

    if resolved_source.suffix.lower() == ".qsch":
        destination = _resolve_output_path(
            output_path,
            workspace_root=normalized_workspace,
            default=resolved_source.with_name(
                f"{resolved_source.stem}-loop-gain-{normalized_method}.qsch"
            ),
            allowed_suffixes=(".qsch",),
        )
        added = add_instruction_service(
            resolved_source,
            workspace_root=normalized_workspace,
            instruction=instruction,
            output_path=destination,
        )
        return PreparedLoopGainAnalysis(
            source_path=resolved_source,
            output_path=added.output_path,
            source_kind="schematic",
            method=normalized_method,
            instruction=instruction,
            reference_example=reference_example,
            method_notes=method_notes,
            expected_loop_gain_signal=normalized_signal,
            warnings=(
                f"Prepared a schematic artifact with one `.ac` directive for "
                f"{normalized_method} loop-gain analysis. Ensure probe infrastructure "
                f"matches QSpice Examples/{reference_example} before simulating.",
                f"After simulation, pass `{normalized_signal}` to "
                "`measure_stability_margins` or `measure_bode_response`.",
            ),
        )

    destination = _resolve_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=resolved_source.with_name(
            f"{resolved_source.stem}-loop-gain-{normalized_method}{resolved_source.suffix}"
        ),
        allowed_suffixes=_NETLIST_SUFFIXES,
    )
    if destination != resolved_source:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(resolved_source, destination)
    _append_instruction_to_netlist(
        destination,
        instruction,
        comment_lines=_render_netlist_comment_block(normalized_method),
    )
    return PreparedLoopGainAnalysis(
        source_path=resolved_source,
        output_path=destination,
        source_kind="netlist",
        method=normalized_method,
        instruction=instruction,
        reference_example=reference_example,
        method_notes=method_notes,
        expected_loop_gain_signal=normalized_signal,
        warnings=(
            f"Prepared a netlist copy with `.ac` plus {normalized_method} guidance comments.",
            f"After simulation, pass `{normalized_signal}` to "
            "`measure_stability_margins` or `measure_bode_response`.",
        ),
    )


__all__ = [
    "LoopGainMethod",
    "PreparedLoopGainAnalysis",
    "SERVICE_SPEC",
    "prepare_loop_gain_analysis",
]
