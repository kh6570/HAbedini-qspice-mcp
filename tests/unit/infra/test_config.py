"""Tests for runtime settings."""

from __future__ import annotations

import re
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings, build_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
_ENV_EXAMPLE_KEY = re.compile(r"^(?:#\s*)?(QSPICE_[A-Z0-9_]+)=")


def _qspice_settings_env_names() -> set[str]:
    prefix = QSpiceSettings.model_config.get("env_prefix", "QSPICE_")
    return {f"{prefix}{field_name.upper()}" for field_name in QSpiceSettings.model_fields}


def _env_example_keys(path: Path = ENV_EXAMPLE_PATH) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _ENV_EXAMPLE_KEY.match(line.strip())
        if match is not None:
            keys.add(match.group(1))
    return keys


def test_env_example_keys_map_to_qspice_settings_fields() -> None:
    documented = _env_example_keys()
    allowed = _qspice_settings_env_names()

    unknown = sorted(documented - allowed)
    assert unknown == [], (
        ".env.example documents env vars with no QSpiceSettings field: " + ", ".join(unknown)
    )


def test_env_example_documents_every_qspice_settings_field() -> None:
    documented = _env_example_keys()
    expected = _qspice_settings_env_names()

    missing = sorted(expected - documented)
    assert missing == [], (
        ".env.example is missing documented entries for QSpiceSettings fields: "
        + ", ".join(missing)
    )


def test_settings_read_executable_from_environment(monkeypatch: object, tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_EXE", str(executable))

    settings = QSpiceSettings().normalized()

    assert settings.exe == executable.resolve()


def test_settings_derive_cache_dir_when_not_configured(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.delenv("QSPICE_CACHE_DIR", raising=False)
    typed_monkeypatch.delenv("QSPICE_EXE", raising=False)

    settings = QSpiceSettings().normalized()

    assert settings.cache_dir is not None


def test_settings_read_telemetry_flag_from_environment(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_TELEMETRY_ENABLED", "true")

    settings = QSpiceSettings().normalized()

    assert settings.telemetry_enabled is True


def test_build_settings_applies_cli_overrides(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    executable = workspace_root / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")

    settings = build_settings(
        transport="sse",
        exe=executable,
        workspace_root=workspace_root,
        telemetry_enabled=True,
    )

    assert settings.transport == "sse"
    assert settings.exe == executable.resolve()
    assert settings.workspace_root == workspace_root.resolve()
    assert settings.telemetry_enabled is True


def test_settings_read_enable_sse_from_environment(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_ENABLE_SSE", "true")

    settings = QSpiceSettings().normalized()

    assert settings.enable_sse is True


def test_settings_resolve_log_folder_and_recipe_path(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"
    recipe_path = tmp_path / "recipes"

    settings = QSpiceSettings(log_folder=log_folder, recipe_path=recipe_path).normalized()

    assert settings.log_folder == log_folder.resolve()
    assert settings.recipe_path == recipe_path.resolve()


def test_build_settings_applies_log_folder_recipe_path_and_sse(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"
    recipe_path = tmp_path / "recipes"

    settings = build_settings(
        log_folder=log_folder,
        recipe_path=recipe_path,
        enable_sse=True,
    )

    assert settings.log_folder == log_folder.resolve()
    assert settings.recipe_path == recipe_path.resolve()
    assert settings.enable_sse is True


def test_settings_default_simulation_timeout() -> None:
    settings = QSpiceSettings().normalized()

    assert settings.timeout_s == 120.0
    assert settings.resolve_timeout_s(None) == 120.0


def test_settings_read_timeout_from_environment(monkeypatch: object) -> None:
    typed_monkeypatch = monkeypatch
    typed_monkeypatch.setenv("QSPICE_TIMEOUT_S", "45")

    settings = QSpiceSettings().normalized()

    assert settings.timeout_s == 45.0
    assert settings.resolve_timeout_s(None) == 45.0


def test_resolve_timeout_prefers_explicit_value() -> None:
    settings = QSpiceSettings(timeout_s=120.0).normalized()

    assert settings.resolve_timeout_s(30.0) == 30.0


def test_resolve_timeout_disables_on_non_positive_values() -> None:
    settings = QSpiceSettings(timeout_s=120.0).normalized()

    assert settings.resolve_timeout_s(0) is None
    assert settings.resolve_timeout_s(-1) is None

    disabled = QSpiceSettings(timeout_s=0).normalized()
    assert disabled.resolve_timeout_s(None) is None
