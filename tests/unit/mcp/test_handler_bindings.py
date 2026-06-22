"""Tests for declarative MCP handler kwarg normalization."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.tools.handler_bindings import (
    _build_service_call_kwargs,
    _normalize_tool_kwargs,
)
from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime
from qspice_mcp.mcp.tool_registry import build_runtime_tool_registry
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic
from qspice_mcp.services.waveform.read_waveform import read_waveform

if TYPE_CHECKING:
    from qspice_mcp.mcp.tools.runtime import QSpiceToolRuntime as RuntimeType


def _runtime(tmp_path: Path) -> QSpiceToolRuntime:
    settings = QSpiceSettings(workspace_root=tmp_path)
    return QSpiceToolRuntime(settings, build_runtime_tool_registry())


def test_build_service_call_kwargs_ignores_null_optional_defaults(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        add_component,
        {
            "schematic_path": "demo.qsch",
            "component_kind": "resistor",
            "reference": "R1",
            "value": "1k",
            "rotation_degrees": None,
            "auto_place": None,
        },
    )
    assert "rotation_degrees" not in kwargs
    assert "auto_place" not in kwargs


def test_build_service_call_kwargs_maps_schematic_path_to_raw_path(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        inspect_schematic,
        {"schematic_path": "demo.qsch"},
    )
    assert kwargs["raw_path"] == "demo.qsch"


def test_build_service_call_kwargs_preserves_explicit_none_defaults(
    tmp_path: Path,
) -> None:
    runtime = _runtime(tmp_path)
    kwargs = _build_service_call_kwargs(
        runtime,
        read_waveform,
        {
            "raw_path": "demo.qraw",
            "signal": "V(out)",
            "component": None,
            "step": None,
        },
    )
    assert "component" not in kwargs
    assert "step" not in kwargs


def test_normalize_tool_kwargs_coerces_text_roles_to_tuple() -> None:
    normalized = _normalize_tool_kwargs(
        "normalize_component_text_rotation",
        {
            "schematic_path": "demo.qsch",
            "reference": "R1",
            "text_roles": ["refdes", "value"],
        },
    )
    assert normalized["text_roles"] == ("refdes", "value")
