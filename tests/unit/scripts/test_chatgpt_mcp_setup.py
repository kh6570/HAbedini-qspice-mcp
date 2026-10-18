# In the name of God, the Most Gracious, the Most Merciful
"""Regression tests for merging and probing ChatGPT desktop's MCP config."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from unittest.mock import Mock

import pytest
from scripts.merge_user_mcp_toml import main, merge_config
from scripts.verify_mcp_stdio import probe_cold_start


@pytest.fixture
def entry() -> dict[str, object]:
    return {
        "type": "stdio",
        "command": r"D:\repo with spaces\.venv\Scripts\python.exe",
        "args": ["-u", "-m", "qspice_mcp", "--workspace-root", r"D:\circuits"],
        "env": {"QSPICE_EXE": r"D:\Program Files\QSPICE\QSPICE64.exe"},
    }


def test_merge_preserves_settings_servers_comments_and_is_repeatable(
    tmp_path: Path, entry: dict[str, object]
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        '# Keep this comment\nmodel = "example"\n'
        '[mcp_servers."other.server"]\ncommand = "other" # Keep this too\n'
        '[projects."D:\\\\work"]\ntrust_level = "trusted"\n',
        encoding="utf-8",
    )
    before = tomllib.loads(config.read_text(encoding="utf-8"))
    merge_config(config, "qspice", entry)
    first = config.read_text(encoding="utf-8")
    merge_config(config, "qspice", entry)
    assert config.read_text(encoding="utf-8") == first
    after = tomllib.loads(first)
    assert after["model"] == before["model"]
    assert after["projects"] == before["projects"]
    assert after["mcp_servers"]["other.server"] == before["mcp_servers"]["other.server"]
    assert "# Keep this comment" in first
    assert "# Keep this too" in first
    qspice = after["mcp_servers"]["qspice"]
    assert qspice["command"] == entry["command"]
    assert qspice["args"] == entry["args"]
    assert qspice["env"] == entry["env"]
    assert "type" not in qspice


def test_cli_creates_config_from_powershell_bom_json(
    tmp_path: Path, entry: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "new" / "config.toml"
    entry_path = tmp_path / "entry.json"
    entry_path.write_text(json.dumps(entry), encoding="utf-8-sig")
    monkeypatch.setattr("sys.argv", ["merge", str(config), "qspice", str(entry_path)])
    assert main() == 0
    assert tomllib.loads(config.read_text(encoding="utf-8"))["mcp_servers"]["qspice"]


@pytest.mark.parametrize("raw", ['model = "unterminated', 'mcp_servers = "wrong type"'])
def test_invalid_config_is_not_overwritten(
    tmp_path: Path, entry: dict[str, object], raw: str
) -> None:
    config = tmp_path / "config.toml"
    config.write_text(raw, encoding="utf-8")
    with pytest.raises((ValueError, TypeError)):
        merge_config(config, "qspice", entry)
    assert config.read_text(encoding="utf-8") == raw


def test_probe_uses_saved_command_args_and_env(
    tmp_path: Path, entry: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "config.toml"
    merge_config(config, "qspice", entry)
    proc = Mock()
    proc.stdout.readline.return_value = b'{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}\n'
    popen = Mock(return_value=proc)
    monkeypatch.setattr(subprocess, "Popen", popen)
    probe_cold_start(python=Path("unused.exe"), workspace_root=tmp_path, budget_s=30, config=config)
    args, kwargs = popen.call_args
    assert args[0] == [entry["command"], *entry["args"]]
    assert kwargs["env"]["QSPICE_EXE"] == entry["env"]["QSPICE_EXE"]


@pytest.mark.parametrize("raw", ["", "[mcp_servers.qspice]\nenabled = false\n"])
def test_probe_rejects_missing_or_disabled_registration(tmp_path: Path, raw: str) -> None:
    config = tmp_path / "config.toml"
    config.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match=r"No mcp_servers\.qspice|qspice is disabled"):
        probe_cold_start(
            python=Path("unused.exe"), workspace_root=tmp_path, budget_s=30, config=config
        )
