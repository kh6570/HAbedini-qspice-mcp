#!/usr/bin/env python3
"""Guard MCP launcher templates against phantom ``QSPICE_*`` env keys.

``.env.example`` is already checked bidirectionally against ``QSpiceSettings``
(see ``tests/unit/infra/test_config.py``). This check extends the same
discipline to the files that write user-level MCP configs, so a dead knob like
``QSPICE_LOG_FORMAT`` cannot be reintroduced into ``%USERPROFILE%\\.cursor\\mcp.json``
or VS Code ``mcp.json`` through the setup script or the AGENTS templates.

Any ``QSPICE_<NAME>`` token in a scanned file must either map to a
``QSpiceSettings`` field or be on the launcher-only allowlist.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings

# Files that define or document MCP server env blocks merged into user configs.
SCANNED_FILES = (
    Path("scripts/setup_mcp.ps1"),
    Path("AGENTS.md"),
)

# Vars consumed only by the launcher/dev tooling, not by QSpiceSettings.
LAUNCHER_ONLY_ENV = frozenset({"QSPICE_DEV_WATCH"})

# Matches QSPICE_FOO but not QSPICE64.exe (digit) or a fragment of a longer word.
_ENV_TOKEN = re.compile(r"(?<![A-Za-z0-9])QSPICE_[A-Z0-9_]+")


@dataclass(frozen=True, slots=True)
class DriftIssue:
    path: Path
    line: int
    token: str


def _allowed_env_names() -> frozenset[str]:
    prefix = QSpiceSettings.model_config.get("env_prefix", "QSPICE_")
    fields = {f"{prefix}{name.upper()}" for name in QSpiceSettings.model_fields}
    return frozenset(fields | LAUNCHER_ONLY_ENV)


def collect_drift_issues(*, root: Path) -> list[DriftIssue]:
    allowed = _allowed_env_names()
    issues: list[DriftIssue] = []
    for rel in SCANNED_FILES:
        path = root / rel
        if not path.is_file():
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in _ENV_TOKEN.finditer(line):
                token = match.group(0)
                if token not in allowed:
                    issues.append(DriftIssue(path=rel, line=lineno, token=token))
    return issues


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    issues = collect_drift_issues(root=root)
    if issues:
        allowed = sorted(_allowed_env_names())
        print(
            f"ERROR: Found {len(issues)} unknown QSPICE_* env key(s) in MCP templates:",
            file=sys.stderr,
        )
        for item in issues:
            print(f"  - {item.path}:{item.line} {item.token}", file=sys.stderr)
        print(f"Allowed keys: {', '.join(allowed)}", file=sys.stderr)
        return 1

    print("OK: MCP launcher templates only reference known QSPICE_* env keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
