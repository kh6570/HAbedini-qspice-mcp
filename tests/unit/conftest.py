"""Unit-test fixtures that keep local developer env from leaking into assertions."""

from __future__ import annotations

import os

import pytest
from pydantic_settings import SettingsConfigDict

from qspice_mcp.infra.config import QSpiceSettings

_QSPICE_SETTINGS_MODEL_CONFIG = SettingsConfigDict(
    env_prefix="QSPICE_",
    env_file=None,
    env_file_encoding="utf-8",
    extra="ignore",
)


@pytest.fixture(autouse=True)
def isolate_qspice_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Match CI: unit tests must not inherit repo ``.env`` or shell ``QSPICE_*`` vars."""
    for key in list(os.environ):
        if key.startswith("QSPICE_"):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setattr(QSpiceSettings, "model_config", _QSPICE_SETTINGS_MODEL_CONFIG)
