"""Guards for the repo-root .mcpb bundle manifest."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MANIFEST_PATH = _REPO_ROOT / "manifest.json"
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def manifest() -> dict[str, object]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_has_required_top_level_fields(manifest: dict[str, object]) -> None:
    for field in ("manifest_version", "name", "version", "description", "author", "server"):
        assert field in manifest, f"manifest.json missing required field {field!r}"
    assert manifest["manifest_version"] == "0.4"
    assert manifest["name"] == "qspice-mcp"


def test_manifest_version_matches_pyproject(manifest: dict[str, object]) -> None:
    pyproject = tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))
    assert manifest["version"] == pyproject["project"]["version"]


def test_manifest_uses_uv_server_with_module_launch(manifest: dict[str, object]) -> None:
    server = manifest["server"]
    assert isinstance(server, dict)
    assert server["type"] == "uv"
    entry_point = server["entry_point"]
    assert isinstance(entry_point, str)
    assert (_REPO_ROOT / entry_point).is_file()

    mcp_config = server["mcp_config"]
    assert isinstance(mcp_config, dict)
    assert mcp_config["command"] == "uv"
    args = mcp_config["args"]
    assert isinstance(args, list)
    assert "qspice_mcp" in args
    assert "--workspace-root" in args
    assert "--session-mode" in args


def test_manifest_user_config_covers_runtime_inputs(manifest: dict[str, object]) -> None:
    user_config = manifest["user_config"]
    assert isinstance(user_config, dict)
    assert set(user_config) >= {"qspice_exe", "workspace_root", "session_mode"}
    assert user_config["qspice_exe"]["required"] is True
    assert user_config["workspace_root"]["required"] is True
    assert user_config["session_mode"]["default"] in {"cold", "auto"}
