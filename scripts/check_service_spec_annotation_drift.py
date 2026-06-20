#!/usr/bin/env python3
"""Assert ServiceSpec.read_only matches MCP tool metadata read_only_hint."""

from __future__ import annotations

import sys
from dataclasses import dataclass

from qspice_mcp.mcp.tool_metadata import TOOL_METADATA
from qspice_mcp.mcp.tool_registry import _DESCRIBE_SERVER_CAPABILITIES_SERVICE
from qspice_mcp.services._internals.service_catalog import build_service_spec_catalog


@dataclass(frozen=True, slots=True)
class AnnotationDriftIssue:
    tool_name: str
    detail: str


def collect_annotation_drift_issues() -> list[AnnotationDriftIssue]:
    issues: list[AnnotationDriftIssue] = []
    specs = build_service_spec_catalog(extra_specs=(_DESCRIBE_SERVER_CAPABILITIES_SERVICE,))
    for spec in specs:
        if spec.phase != "implemented":
            continue
        metadata = TOOL_METADATA.get(spec.name)
        if metadata is None:
            issues.append(
                AnnotationDriftIssue(
                    tool_name=spec.name,
                    detail="missing TOOL_METADATA entry",
                )
            )
            continue
        annotations = metadata.get("annotations")
        if not isinstance(annotations, dict):
            hint = False
        else:
            hint = bool(annotations.get("read_only_hint", False))
        if spec.read_only != hint:
            issues.append(
                AnnotationDriftIssue(
                    tool_name=spec.name,
                    detail=(f"service.read_only={spec.read_only} metadata.read_only_hint={hint}"),
                )
            )
    return issues


def main() -> int:
    issues = collect_annotation_drift_issues()
    if issues:
        print(
            f"ERROR: Found {len(issues)} ServiceSpec vs metadata read_only drift issue(s):",
            file=sys.stderr,
        )
        for issue in issues:
            print(f"  - {issue.tool_name}: {issue.detail}", file=sys.stderr)
        return 1

    print("OK: ServiceSpec.read_only matches MCP metadata read_only_hint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
