#!/usr/bin/env python3
"""Assert MCP prompt definitions, builders, and registration stay in sync.

Checks:
- every ``get_prompt_definitions()`` name has a matching prompt builder
- every prompt builder maps to a declared definition (no orphan builders)
- ``register_prompts`` binds exactly the declared definition names
- prompt names are unique
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from qspice_mcp.mcp.prompts import _PROMPT_BUILDERS, get_prompt_definitions


@dataclass(frozen=True, slots=True)
class PromptDriftIssue:
    category: str
    detail: str


class _RecordingPromptApp:
    """Minimal stand-in that records the names register_prompts binds."""

    def __init__(self) -> None:
        self.registered: list[str] = []

    def prompt(self, *, name: str, title: str, description: str):
        del title, description
        self.registered.append(name)

        def _decorator(func):
            return func

        return _decorator


def _registered_prompt_names() -> list[str]:
    from qspice_mcp.mcp.prompts.registration import register_prompts  # noqa: PLC0415

    app = _RecordingPromptApp()
    register_prompts(app, get_prompt_definitions())  # type: ignore[arg-type]
    return app.registered


def collect_prompt_drift_issues() -> list[PromptDriftIssue]:
    definitions = get_prompt_definitions()
    definition_names = [definition.name for definition in definitions]
    definition_set = set(definition_names)
    builder_set = set(_PROMPT_BUILDERS)

    issues: list[PromptDriftIssue] = []

    duplicates = sorted({name for name in definition_names if definition_names.count(name) > 1})
    if duplicates:
        issues.append(PromptDriftIssue("duplicate-definition", ", ".join(duplicates)))

    missing_builders = sorted(definition_set - builder_set)
    if missing_builders:
        issues.append(PromptDriftIssue("definition-without-builder", ", ".join(missing_builders)))

    orphan_builders = sorted(builder_set - definition_set)
    if orphan_builders:
        issues.append(PromptDriftIssue("builder-without-definition", ", ".join(orphan_builders)))

    registered = _registered_prompt_names()
    registered_set = set(registered)
    not_registered = sorted(definition_set - registered_set)
    if not_registered:
        issues.append(PromptDriftIssue("definition-not-registered", ", ".join(not_registered)))
    extra_registered = sorted(registered_set - definition_set)
    if extra_registered:
        issues.append(
            PromptDriftIssue("registered-without-definition", ", ".join(extra_registered))
        )

    return issues


def main() -> int:
    issues = collect_prompt_drift_issues()
    if issues:
        print(f"ERROR: Found {len(issues)} MCP prompt drift issue(s):", file=sys.stderr)
        for item in issues:
            print(f"  - [{item.category}] {item.detail}", file=sys.stderr)
        return 1
    print(f"OK: {len(get_prompt_definitions())} MCP prompt(s) match builders and registration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
