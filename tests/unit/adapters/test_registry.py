"""Tests for adapter registration and selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.adapters.probe import ProbeResult
from qspice_mcp.adapters.registry import describe_adapters, get_registered_adapters, select_adapter
from qspice_mcp.core.exceptions import AdapterNotFoundError

if TYPE_CHECKING:
    from pathlib import Path


def test_get_registered_adapters_has_current_cli() -> None:
    adapters = get_registered_adapters()

    assert len(adapters) == 1
    assert adapters[0].key == "cli.v1"


def test_select_adapter_returns_current_cli(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    probe = ProbeResult(configured=True, executable=executable, exists=True, source="configured")

    adapter = select_adapter(probe)

    assert adapter.key == "cli.v1"
    assert adapter.base_command(probe) == (str(executable.resolve()),)


def test_select_adapter_raises_when_no_executable() -> None:
    probe = ProbeResult(configured=False, executable=None, exists=False, source="unavailable")

    with pytest.raises(AdapterNotFoundError):
        select_adapter(probe)


def test_describe_adapters_marks_availability(tmp_path: Path) -> None:
    executable = tmp_path / "QSPICE64.exe"
    executable.write_text("", encoding="utf-8")
    probe = ProbeResult(configured=True, executable=executable, exists=True, source="configured")

    descriptions = describe_adapters(probe)

    assert descriptions[0].available is True
    assert descriptions[0].summary()["capabilities"]["cli_invocation"] is True
