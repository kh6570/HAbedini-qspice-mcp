"""Service for surfacing `.plot`, `.print`, `.probe`, and `.abscissa` hints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from qspice_mcp.services._shared.paths import validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation.generate_netlist import (
    generate_netlist as generate_netlist_service,
)

if TYPE_CHECKING:
    from pathlib import Path

_KNOWN_ANALYSES = {"AC", "DC", "TRAN", "TR", "NOISE", "TF", "OP"}


@dataclass(frozen=True, slots=True)
class PlotSuggestion:
    """One plot-oriented directive suggestion extracted from source text."""

    kind: Literal["plot", "print", "probe"]
    analysis: str | None
    expressions: tuple[str, ...]
    directive: str


@dataclass(frozen=True, slots=True)
class PlotSuggestionCatalog:
    """Collected plot-oriented directive suggestions for one source."""

    source_path: Path
    netlist_path: Path
    source_kind: Literal["schematic", "netlist"]
    abscissa_expression: str | None
    suggestions: tuple[PlotSuggestion, ...]
    warnings: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="list_plot_suggestions",
    title="List Plot Suggestions",
    summary=(
        "Inspect a netlist-oriented source and surface documented `.plot`, "
        "`.print`, `.probe`, and `.abscissa` hints."
    ),
    phase="implemented",
    read_only=False,
)


def _combine_directive_lines(text: str) -> tuple[str, ...]:
    combined: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.startswith("+") and combined:
            combined[-1] = f"{combined[-1]} {stripped[1:].strip()}".strip()
            continue
        combined.append(stripped)
    return tuple(combined)


def _parse_plot_directive(directive: str) -> PlotSuggestion:
    tokens = directive.split()
    kind = tokens[0][1:].lower()
    remainder = tokens[1:]
    analysis: str | None = None
    if remainder and remainder[0].upper() in _KNOWN_ANALYSES:
        analysis = remainder[0].upper()
        remainder = remainder[1:]
    normalized_kind: Literal["plot", "print", "probe"]
    if kind == "print":
        normalized_kind = "print"
    elif kind == "probe":
        normalized_kind = "probe"
    else:
        normalized_kind = "plot"
    return PlotSuggestion(
        kind=normalized_kind,
        analysis=analysis,
        expressions=tuple(remainder),
        directive=directive,
    )


def list_plot_suggestions(
    source_path: str | Path,
    *,
    workspace_root: Path,
    netlist_output_path: str | Path | None = None,
) -> PlotSuggestionCatalog:
    """Extract plot-oriented directives from a netlist or staged schematic netlist."""

    normalized_workspace = workspace_root.resolve(strict=False)
    resolved_source = validate_existing_file(
        source_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )

    source_kind: Literal["schematic", "netlist"] = "netlist"
    netlist_path = resolved_source
    warnings: tuple[str, ...] = ()
    if resolved_source.suffix.lower() == ".qsch":
        generated = generate_netlist_service(
            resolved_source,
            workspace_root=normalized_workspace,
            output_path=netlist_output_path,
        )
        source_kind = "schematic"
        netlist_path = generated.netlist_path
        warnings = generated.warnings
    elif netlist_output_path is not None:
        generated = generate_netlist_service(
            resolved_source,
            workspace_root=normalized_workspace,
            output_path=netlist_output_path,
        )
        netlist_path = generated.netlist_path
        warnings = generated.warnings

    text = netlist_path.read_text(encoding="utf-8", errors="replace")
    abscissa_expression: str | None = None
    suggestions: list[PlotSuggestion] = []
    for directive in _combine_directive_lines(text):
        keyword = directive.split(maxsplit=1)[0].lower()
        if keyword == ".abscissa":
            abscissa_expression = directive[len(".abscissa") :].strip() or None
            continue
        if keyword in {".plot", ".print", ".probe"}:
            suggestions.append(_parse_plot_directive(directive))

    return PlotSuggestionCatalog(
        source_path=resolved_source,
        netlist_path=netlist_path,
        source_kind=source_kind,
        abscissa_expression=abscissa_expression,
        suggestions=tuple(suggestions),
        warnings=warnings,
    )


__all__ = ["SERVICE_SPEC", "PlotSuggestion", "PlotSuggestionCatalog", "list_plot_suggestions"]
