# In the name of God, the Most Gracious, the Most Merciful
"""One MCP session: create a schematic, check it, simulate, and read one measure."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server

if TYPE_CHECKING:
    from mcp.types import CallToolResult

pytestmark = pytest.mark.integration


def _require_qspice_exe() -> Path:
    raw = os.environ.get("QSPICE_EXE", "").strip()
    if not raw:
        pytest.skip("QSPICE_EXE is not set.")
    executable = Path(raw)
    if not executable.is_file():
        pytest.skip("QSPICE_EXE does not point at an existing QSpice executable.")
    return executable


def _payload(result: CallToolResult) -> dict[str, object]:
    if result.isError:
        text = result.content[0].text if result.content else "tool call failed"
        raise AssertionError(text)
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    text = result.content[0].text if result.content else ""
    parsed = json.loads(text)
    assert isinstance(parsed, dict)
    return parsed


@pytest.mark.anyio
async def test_mcp_create_check_simulate_and_measure(tmp_path: Path) -> None:
    executable = _require_qspice_exe()
    server = create_server(QSpiceSettings(exe=executable, workspace_root=tmp_path))

    async with create_connected_server_and_client_session(server.app) as session:
        created = _payload(
            await session.call_tool(
                "create_starter_schematic",
                {"output_path": "starter.qsch", "analysis_instruction": ".tran 1m"},
            )
        )
        checked = _payload(
            await session.call_tool("check_schematic", {"schematic_path": "starter.qsch"})
        )
        simulated = _payload(
            await session.call_tool(
                "run_simulation",
                {"source_path": "starter.qsch", "ascii_raw": True},
            )
        )
        raw_path = str(simulated["raw_path"])
        catalog = _payload(await session.call_tool("list_signals", {"raw_path": raw_path}))
        signals = catalog["signals"]
        assert isinstance(signals, list)
        assert signals
        signal_name = str(signals[0]["name"])
        measured = _payload(
            await session.call_tool(
                "measure_waveform",
                {"raw_path": raw_path, "signal": signal_name, "operation": "mean"},
            )
        )

    assert str(created["output_path"]).endswith("starter.qsch")
    assert checked["ok"] is True
    findings = checked["findings"]
    assert isinstance(findings, list)
    if findings:
        assert "fixable" in findings[0]
        assert "location" in findings[0]
    assert simulated["exit_code"] == 0
    assert isinstance(measured["value"], int | float)
