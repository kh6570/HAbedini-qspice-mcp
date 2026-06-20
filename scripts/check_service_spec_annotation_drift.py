#!/usr/bin/env python3
"""Assert enriched ServiceSpec rows expose MCP contracts and annotation hints."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from qspice_mcp.mcp.tool_registry import (
    _DESCRIBE_SERVER_CAPABILITIES_SERVICE,
    resolve_tool_annotations,
)
from qspice_mcp.services._internals.service_catalog import (
    build_mcp_contract_catalog,
    build_service_spec_catalog,
)


@dataclass(frozen=True, slots=True)
class AnnotationDriftIssue:
    tool_name: str
    detail: str


def collect_annotation_drift_issues() -> list[AnnotationDriftIssue]:
    issues: list[AnnotationDriftIssue] = []
    contracts = build_mcp_contract_catalog()
    specs = build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))
    for spec in specs:
        if spec.phase != "implemented":
            continue
        if spec.name not in contracts:
            issues.append(
                AnnotationDriftIssue(
                    tool_name=spec.name,
                    detail="missing MCP contract entry",
                )
            )
            continue
        if spec.input_schema is None:
            issues.append(
                AnnotationDriftIssue(
                    tool_name=spec.name,
                    detail="missing input_schema on enriched ServiceSpec",
                )
            )
            continue
        resolved = resolve_tool_annotations(spec)
        expected_idempotent = spec.idempotent if spec.idempotent is not None else spec.read_only
        checks = (
            ("read_only", spec.read_only, resolved.read_only_hint),
            ("destructive", spec.destructive, resolved.destructive_hint),
            ("idempotent", expected_idempotent, resolved.idempotent_hint),
        )
        for label, expected, actual in checks:
            if expected != actual:
                issues.append(
                    AnnotationDriftIssue(
                        tool_name=spec.name,
                        detail=f"service.{label}={expected} resolved.{label}_hint={actual}",
                    )
                )
    return issues


def main() -> int:
    issues = collect_annotation_drift_issues()
    if issues:
        print(
            f"ERROR: Found {len(issues)} ServiceSpec MCP contract drift issue(s):",
            file=sys.stderr,
        )
        for issue in issues:
            print(f"  - {issue.tool_name}: {issue.detail}", file=sys.stderr)
        return 1

    print("OK: ServiceSpec MCP contracts and annotation hints are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
