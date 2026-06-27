"""Tests for the session-mode resolver."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.infra import session_mode
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.infra.session_mode import (
    SessionStrategy,
    resolve_session_plan,
    resolve_session_plan_for_settings,
)

if TYPE_CHECKING:
    import pytest


def test_cold_mode_always_cold_launches() -> None:
    plan = resolve_session_plan(session_mode="cold", live_gui_available=True)
    assert plan.strategy is SessionStrategy.COLD_LAUNCH
    assert "cold" in plan.reason


def test_auto_mode_reuses_live_gui_when_available() -> None:
    plan = resolve_session_plan(session_mode="auto", live_gui_available=True)
    assert plan.strategy is SessionStrategy.REUSE_LIVE_GUI
    assert "reuse" in plan.reason.lower()


def test_auto_mode_falls_back_to_cold_when_no_live_gui() -> None:
    plan = resolve_session_plan(session_mode="auto", live_gui_available=False)
    assert plan.strategy is SessionStrategy.COLD_LAUNCH


def test_settings_default_session_mode_is_cold() -> None:
    assert QSpiceSettings(workspace_root=Path.cwd()).session_mode == "cold"


def test_live_gui_unavailable_off_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_mode.sys, "platform", "linux")
    settings = QSpiceSettings(workspace_root=Path.cwd(), live_gui_bridge_command=("bridge.exe",))
    assert session_mode.live_gui_session_available(settings) is False


def test_live_gui_available_requires_bridge_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(session_mode.sys, "platform", "win32")
    without_bridge = QSpiceSettings(workspace_root=Path.cwd())
    with_bridge = QSpiceSettings(
        workspace_root=Path.cwd(),
        live_gui_bridge_command=("bridge.exe", "--serve"),
    )
    assert session_mode.live_gui_session_available(without_bridge) is False
    assert session_mode.live_gui_session_available(with_bridge) is True


def test_resolve_for_settings_uses_session_mode_and_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(session_mode.sys, "platform", "win32")
    settings = QSpiceSettings(
        workspace_root=Path.cwd(),
        session_mode="auto",
        live_gui_bridge_command=("bridge.exe",),
    )
    plan = resolve_session_plan_for_settings(settings)
    assert plan.strategy is SessionStrategy.REUSE_LIVE_GUI
