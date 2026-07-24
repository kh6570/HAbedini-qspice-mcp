"""Service for staging a source with a documented `.dc` directive."""

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
    from collections.abc import Sequence
    from pathlib import Path

_NETLIST_SUFFIXES = (".net", ".cir")
_DC_SWEEP_MODES = frozenset({"lin", "oct", "dec", "list"})


@dataclass(frozen=True, slots=True)
class PreparedDcSweep:
    """Metadata for one source staged with a `.dc` directive."""

    source_path: Path
    output_path: Path
    source_kind: Literal["schematic", "netlist"]
    instruction: str
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="prepare_dc_sweep",
    title="Prepare DC Sweep",
    summary="Stage a schematic or netlist with a documented `.dc` directive.",
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


def _render_dc_dimension(
    source: str,
    *,
    sweep_mode: str,
    start: str | None,
    stop: str | None,
    step: str | None,
    list_values: Sequence[str] | None,
    label: str,
) -> tuple[str, ...]:
    normalized_mode = sweep_mode.strip().lower()
    if normalized_mode not in _DC_SWEEP_MODES:
        allowed = ", ".join(sorted(_DC_SWEEP_MODES))
        raise ValueError(f"{label} sweep mode must be one of: {allowed}")
    normalized_source = source.strip()
    if not normalized_source:
        raise ValueError(f"{label} source must not be blank.")

    if normalized_mode == "list":
        values = tuple(value.strip() for value in (list_values or ()) if value.strip())
        if not values:
            raise ValueError(f"{label} list sweep requires at least one value in list_values.")
        return (normalized_source, "list", *values)

    if start is None or stop is None or step is None:
        raise ValueError(
            f"{label} `{normalized_mode}` sweep requires start, stop, and step "
            "(step is the increment for `lin` and points per octave/decade for `oct`/`dec`)."
        )
    tokens: tuple[str, ...] = (normalized_source, start.strip(), stop.strip(), step.strip())
    if normalized_mode == "lin":
        return tokens
    return (normalized_mode, *tokens)


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


def prepare_dc_sweep(
    source_path: str | Path,
    *,
    workspace_root: Path,
    source: str,
    start: str | None = None,
    stop: str | None = None,
    step: str | None = None,
    sweep_mode: str = "lin",
    list_values: Sequence[str] | None = None,
    second_source: str | None = None,
    second_start: str | None = None,
    second_stop: str | None = None,
    second_step: str | None = None,
    second_sweep_mode: str = "lin",
    second_list_values: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> PreparedDcSweep:
    """Stage a schematic or netlist with one documented `.dc` directive.

    Supports linear, octave, decade, and explicit list sweeps, with an optional
    second sweep dimension for curve tracing (QSpice allows up to six).
    """

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )
    tokens: list[str] = [".dc"]
    tokens.extend(
        _render_dc_dimension(
            source,
            sweep_mode=sweep_mode,
            start=start,
            stop=stop,
            step=step,
            list_values=list_values,
            label="primary",
        )
    )
    if second_source is not None:
        tokens.extend(
            _render_dc_dimension(
                second_source,
                sweep_mode=second_sweep_mode,
                start=second_start,
                stop=second_stop,
                step=second_step,
                list_values=second_list_values,
                label="second",
            )
        )
    instruction = " ".join(tokens)

    if resolved_source.suffix.lower() == ".qsch":
        destination = _resolve_output_path(
            output_path,
            workspace_root=normalized_workspace,
            default=resolved_source.with_name(f"{resolved_source.stem}-dc.qsch"),
            allowed_suffixes=(".qsch",),
        )
        added = add_instruction_service(
            resolved_source,
            workspace_root=normalized_workspace,
            instruction=instruction,
            output_path=destination,
        )
        return PreparedDcSweep(
            source_path=resolved_source,
            output_path=added.output_path,
            source_kind="schematic",
            instruction=instruction,
            warnings=(
                "Prepared a schematic artifact with one `.dc` directive. "
                "Run simulation on the staged output.",
            ),
        )

    destination = _resolve_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=resolved_source.with_name(f"{resolved_source.stem}-dc{resolved_source.suffix}"),
        allowed_suffixes=_NETLIST_SUFFIXES,
    )
    if destination != resolved_source:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(resolved_source, destination)
    _append_instruction_to_netlist(destination, instruction)
    return PreparedDcSweep(
        source_path=resolved_source,
        output_path=destination,
        source_kind="netlist",
        instruction=instruction,
        warnings=("Prepared a netlist copy with one `.dc` directive.",),
    )


__all__ = ["SERVICE_SPEC", "PreparedDcSweep", "prepare_dc_sweep"]
