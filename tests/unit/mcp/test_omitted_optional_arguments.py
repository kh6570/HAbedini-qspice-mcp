# In the name of God, the Most Gracious, the Most Merciful
"""MCP clients omit optional arguments; those must not override Python defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services._internals.live_gui_manager import LiveGuiSessionManager

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.anyio
async def test_poll_live_gui_events_omits_optional_arguments(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def fake_poll(
        self: LiveGuiSessionManager,
        session_id: str,
        *,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> dict[str, object]:
        del self
        captured["session_id"] = session_id
        captured["after_sequence"] = after_sequence
        captured["limit"] = limit
        return {
            "session_id": session_id,
            "after_sequence": after_sequence,
            "limit": limit,
            "events": [],
        }

    monkeypatch.setattr(LiveGuiSessionManager, "poll_live_gui_session_events", fake_poll)
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    await server.app.call_tool("poll_live_gui_session_events", {"session_id": "sess-1"})

    assert captured == {"session_id": "sess-1", "after_sequence": 0, "limit": 50}
