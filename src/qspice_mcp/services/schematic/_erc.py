"""Repo-owned read-only ERC-style checks for schematics and netlists.

These checks are intentionally conservative: they reuse the clean-room
connectivity model for ``.qsch`` files and a lightweight token scan for
``.net``/``.cir`` files. They never mutate inputs and report findings with a
stable severity (``error``/``warning``/``info``) and machine-readable ``code``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qspice_mcp.services.schematic._connectivity import ConnectivityModel

_GROUND_NODE = "0"
_VALUE_OPTIONAL_SYMBOLS = frozenset({"G", "GROUND", "X"})
_DLL_MARKERS = (".dll", "verilog", "c-block")
# Minimum tokens for a netlist element line: a refdes plus at least one node.
_MIN_ELEMENT_TOKENS = 2
# First-letter -> number of leading node tokens for netlist node extraction.
_NETLIST_NODE_COUNTS = {
    "R": 2,
    "C": 2,
    "L": 2,
    "V": 2,
    "I": 2,
    "D": 2,
    "E": 4,
    "G": 4,
    "Q": 3,
    "J": 3,
    "M": 4,
}


@dataclass(frozen=True, slots=True)
class ErcFinding:
    """One ERC observation."""

    severity: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ErcReport:
    """Aggregated ERC findings for one artifact."""

    ok: bool
    error_count: int
    warning_count: int
    info_count: int
    findings: tuple[ErcFinding, ...]


def _build_report(findings: list[ErcFinding]) -> ErcReport:
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    infos = sum(1 for finding in findings if finding.severity == "info")
    return ErcReport(
        ok=errors == 0,
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
        findings=tuple(findings),
    )


def _is_dll_symbol(text: str) -> bool:
    lowered = text.lower().replace("\ufffd", "").replace("ø", "").strip("() ").strip()
    return any(marker in lowered for marker in _DLL_MARKERS)


def _value_is_required(*, symbol: str, kind: str) -> bool:
    for candidate in (symbol.upper(), kind.upper()):
        if candidate in _VALUE_OPTIONAL_SYMBOLS:
            return False
    return not (_is_dll_symbol(symbol) or _is_dll_symbol(kind))


def evaluate_schematic_connectivity(model: ConnectivityModel) -> ErcReport:
    """Apply ERC rules to a clean-room connectivity model."""

    findings: list[ErcFinding] = []

    if model.components and not model.ground_present:
        findings.append(
            ErcFinding(
                severity="error",
                code="missing_ground",
                message=(
                    "No ground reference (node 0) was found. Add a GND net label "
                    "on the circuit's reference node."
                ),
            )
        )

    reference_counts = Counter(
        component.reference for component in model.components if component.reference
    )
    for reference, count in sorted(reference_counts.items()):
        if count > 1:
            findings.append(
                ErcFinding(
                    severity="error",
                    code="duplicate_reference",
                    message=f"Reference designator {reference} is used by {count} components.",
                )
            )

    for conflict in model.conflicts:
        labels = ", ".join(conflict.labels)
        findings.append(
            ErcFinding(
                severity="error",
                code="conflicting_net_labels",
                message=f"Conflicting net labels on one connection: {labels}.",
            )
        )

    for group in model.nets:
        if len(group.members) == 1 and not group.labeled:
            member = group.members[0]
            findings.append(
                ErcFinding(
                    severity="warning",
                    code="floating_pin",
                    message=(
                        f"Pin {member.pin} of {member.reference} on net {group.name} has no "
                        "other connection. Add a wire or net label."
                    ),
                )
            )

    for component in model.components:
        if component.reference is None:
            continue
        if _value_is_required(symbol=component.symbol, kind=component.kind) and not component.value:
            findings.append(
                ErcFinding(
                    severity="warning",
                    code="missing_value",
                    message=(f"Component {component.reference} has no value or model assigned."),
                )
            )

    return _build_report(findings)


def _iter_netlist_elements(netlist_text: str) -> list[list[str]]:
    elements: list[list[str]] = []
    for raw_line in netlist_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("*", ".", "+")):
            continue
        tokens = line.split()
        if len(tokens) < _MIN_ELEMENT_TOKENS or not tokens[0][:1].isalpha():
            continue
        elements.append(tokens)
    return elements


def _netlist_nodes(tokens: list[str]) -> list[str]:
    prefix = tokens[0][:1].upper()
    if prefix == "X":
        return tokens[1:-1] if len(tokens) > _MIN_ELEMENT_TOKENS else tokens[1:]
    node_count = _NETLIST_NODE_COUNTS.get(prefix, 2)
    return tokens[1 : 1 + node_count]


def evaluate_netlist(netlist_text: str) -> ErcReport:
    """Apply conservative ERC rules to a `.net`/`.cir` netlist body."""

    findings: list[ErcFinding] = []
    elements = _iter_netlist_elements(netlist_text)

    reference_counts = Counter(tokens[0] for tokens in elements)
    for reference, count in sorted(reference_counts.items()):
        if count > 1:
            findings.append(
                ErcFinding(
                    severity="error",
                    code="duplicate_reference",
                    message=f"Reference designator {reference} appears on {count} netlist lines.",
                )
            )

    node_usage: Counter[str] = Counter()
    for tokens in elements:
        for node in _netlist_nodes(tokens):
            node_usage[node] += 1

    if elements and _GROUND_NODE not in node_usage:
        findings.append(
            ErcFinding(
                severity="error",
                code="missing_ground",
                message="No ground node 0 was found in the netlist.",
            )
        )

    for node, count in sorted(node_usage.items()):
        if node == _GROUND_NODE:
            continue
        if count == 1:
            findings.append(
                ErcFinding(
                    severity="warning",
                    code="single_connection_node",
                    message=f"Node {node} connects to only one element pin.",
                )
            )

    return _build_report(findings)


__all__ = [
    "ErcFinding",
    "ErcReport",
    "evaluate_netlist",
    "evaluate_schematic_connectivity",
]
