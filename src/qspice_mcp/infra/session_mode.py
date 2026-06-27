"""Resolve how a simulation should obtain a QSpice session.

``session_mode=cold`` (the default) always cold-launches a fresh CLI simulation.
``session_mode=auto`` prefers reusing an already-available live-GUI session before
falling back to a cold launch. The decision itself is a pure function so it can be
unit-tested without a live QSpice; the only environment-dependent input is whether a
live-GUI session is currently reachable.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from qspice_mcp.infra.config import QSpiceSettings

SessionMode = Literal["cold", "auto"]


class SessionStrategy(StrEnum):
    """How a simulation will acquire its QSpice session."""

    COLD_LAUNCH = "cold_launch"
    REUSE_LIVE_GUI = "reuse_live_gui"


@dataclass(frozen=True, slots=True)
class SessionPlan:
    """The resolved session strategy plus a human-readable rationale."""

    strategy: SessionStrategy
    reason: str


def resolve_session_plan(
    *,
    session_mode: SessionMode,
    live_gui_available: bool,
) -> SessionPlan:
    """Decide whether to reuse a live-GUI session or cold-launch (pure)."""

    if session_mode == "auto" and live_gui_available:
        return SessionPlan(
            strategy=SessionStrategy.REUSE_LIVE_GUI,
            reason="session_mode=auto and a live-GUI session is available; reuse it.",
        )
    if session_mode == "auto":
        return SessionPlan(
            strategy=SessionStrategy.COLD_LAUNCH,
            reason="session_mode=auto but no live-GUI session is available; cold-launch.",
        )
    return SessionPlan(
        strategy=SessionStrategy.COLD_LAUNCH,
        reason="session_mode=cold; always cold-launch a fresh simulation.",
    )


def bridge_configured(settings: QSpiceSettings) -> bool:
    """Return whether a live-GUI bridge *could* run on this host.

    This only checks the static prerequisites (Windows host plus a configured bridge
    command), mirroring ``describe_live_gui_support`` without inverting the dependency
    rule. It does **not** prove that a session is currently running and reachable — use
    ``running_session_available`` for that runtime check.
    """

    bridge_command = tuple(
        str(item).strip() for item in settings.live_gui_bridge_command if str(item).strip()
    )
    return sys.platform == "win32" and bool(bridge_command)


# Backwards-compatible alias: historically this name meant "bridge configured".
def live_gui_session_available(settings: QSpiceSettings) -> bool:
    """Deprecated alias for :func:`bridge_configured` (static prerequisite check)."""

    return bridge_configured(settings)


def resolve_session_plan_for_settings(
    settings: QSpiceSettings,
    *,
    running_session_available: bool | None = None,
) -> SessionPlan:
    """Resolve the session plan for one settings object.

    When ``running_session_available`` is provided it gates reuse on an actually
    reachable session (bridge configured **and** a running session), matching the
    documented ``auto`` semantics. When omitted, only the static bridge prerequisite is
    considered (used by callers that have no live registry to inspect).
    """

    available = bridge_configured(settings)
    if running_session_available is not None:
        available = available and running_session_available
    return resolve_session_plan(
        session_mode=settings.session_mode,
        live_gui_available=available,
    )


__all__ = [
    "SessionMode",
    "SessionPlan",
    "SessionStrategy",
    "bridge_configured",
    "live_gui_session_available",
    "resolve_session_plan",
    "resolve_session_plan_for_settings",
]
