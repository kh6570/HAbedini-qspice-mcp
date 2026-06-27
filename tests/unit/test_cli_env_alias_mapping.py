"""Guard: the documented CLI<->env alias mapping stays in sync with the code.

Roadmap item "CLI <-> env alias mapping": every setting-bearing launcher flag
must mirror a ``QSPICE_*`` environment variable (CLI wins), and that mapping must
be documented in ``docs/user-guide.md``. This test enforces all three sides
(argparse flags, ``QSpiceSettings`` fields, and the user-guide table) agree.
"""

from __future__ import annotations

import re
from pathlib import Path

from qspice_mcp.__main__ import build_arg_parser
from qspice_mcp.infra.config import QSpiceSettings

REPO_ROOT = Path(__file__).resolve().parents[2]
USER_GUIDE = REPO_ROOT / "docs" / "user-guide.md"

# Authoritative mapping: CLI flag -> QSpiceSettings field it overrides (CLI wins).
CLI_FLAG_TO_FIELD = {
    "--transport": "transport",
    "--session-mode": "session_mode",
    "--qspice-exe": "exe",
    "--workspace-root": "workspace_root",
    "--log-level": "log_level",
    "--log-folder": "log_folder",
    "--recipe-path": "recipe_path",
}

# Settings exposed only through the environment (no CLI flag).
ENV_ONLY_FIELDS = ("enable_sse",)

# Action-only flags that carry no setting/env mirror (mode switches, reports).
ACTION_ONLY_FLAGS = {
    "-h",
    "--help",
    "--version",
    "--describe",
    "--setup",
    "--watchdog",
    "--parent-pid",
    "--child-pid",
    "--watchdog-poll-interval",
}


def _field_to_env(field: str) -> str:
    return f"QSPICE_{field.upper()}"


def _parser_option_flags() -> set[str]:
    flags: set[str] = set()
    for action in build_arg_parser()._actions:
        flags.update(action.option_strings)
    return flags


def _documented_rows() -> dict[str, str]:
    """Return {cli_flag_or_'(none)': env_var} parsed from the user-guide table."""

    text = USER_GUIDE.read_text(encoding="utf-8")
    rows: dict[str, str] = {}
    row_pattern = re.compile(r"^\|\s*(.+?)\s*\|\s*`?(QSPICE_[A-Z_]+)`?\s*\|")
    for line in text.splitlines():
        match = row_pattern.match(line)
        if match is None:
            continue
        cli_cell = match.group(1).strip().strip("`")
        env_var = match.group(2).strip()
        rows[cli_cell] = env_var
    return rows


def test_every_cli_override_flag_maps_to_a_real_settings_field() -> None:
    valid_fields = set(QSpiceSettings.model_fields)
    for flag, field in CLI_FLAG_TO_FIELD.items():
        assert field in valid_fields, f"{flag} maps to unknown settings field {field!r}"


def test_parser_setting_flags_match_the_authoritative_mapping() -> None:
    parser_setting_flags = {
        flag
        for flag in _parser_option_flags()
        if flag not in ACTION_ONLY_FLAGS and flag.startswith("--")
    }
    assert parser_setting_flags == set(CLI_FLAG_TO_FIELD), (
        "argparse setting flags drifted from the documented CLI<->env mapping; "
        "update CLI_FLAG_TO_FIELD and docs/user-guide.md together."
    )


def test_user_guide_documents_every_cli_env_alias() -> None:
    documented = _documented_rows()
    for flag, field in CLI_FLAG_TO_FIELD.items():
        assert documented.get(flag) == _field_to_env(field), (
            f"docs/user-guide.md must document {flag} -> {_field_to_env(field)}"
        )


def test_user_guide_documents_env_only_settings() -> None:
    documented = _documented_rows()
    documented_env_vars = set(documented.values())
    for field in ENV_ONLY_FIELDS:
        env_var = _field_to_env(field)
        assert env_var in documented_env_vars, (
            f"docs/user-guide.md must document the env-only setting {env_var}"
        )
