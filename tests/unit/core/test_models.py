"""Tests for domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from qspice_mcp.core.models import (
    Analysis,
    AnalysisKind,
    Component,
    Netlist,
    SimulationResult,
    Waveform,
)


def build_component() -> Component:
    """Create a representative component for tests."""
    return Component(refdes="R1", kind="R", nodes=("in", "out"), value="1k")


def test_component_is_frozen() -> None:
    component = build_component()
    with pytest.raises(FrozenInstanceError):
        component.value = "2k"  # type: ignore[misc]


def test_waveform_is_frozen() -> None:
    waveform = Waveform(name="V(out)", x=np.array([0.0]), y=np.array([1.0]))
    with pytest.raises(FrozenInstanceError):
        waveform.name = "V(in)"  # type: ignore[misc]


def test_netlist_find_matches_case_insensitively() -> None:
    component = build_component()
    netlist = Netlist(
        title="demo",
        components=[component],
        directives=[".op"],
        analyses=[Analysis(kind=AnalysisKind.OP)],
        raw="demo\n.op\n.end\n",
    )
    assert netlist.find("r1") == component


def test_simulation_result_keeps_paths_and_analysis() -> None:
    analysis = Analysis(kind=AnalysisKind.TRAN, params={"tstop": 1e-3})
    result = SimulationResult(
        run_id="run-1",
        raw_path=Path("sample.qraw"),
        log_path=Path("sample.log"),
        analysis=analysis,
        signals=["V(out)"],
        duration_s=0.25,
        exit_code=0,
    )
    assert result.raw_path.name == "sample.qraw"
    assert result.analysis.kind is AnalysisKind.TRAN
