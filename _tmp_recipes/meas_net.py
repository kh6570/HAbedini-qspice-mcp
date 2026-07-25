"""Measure mean V(out) from a .qraw produced by try_net.py."""

from __future__ import annotations

import sys
from pathlib import Path

from qspice_mcp.services.waveform.measure_waveform import measure_waveform

WS = Path(__file__).resolve().parent / "ws_build"

name = sys.argv[1]
value = measure_waveform(
    f"{name}.qraw",
    workspace_root=WS,
    signal="V(out)",
    operation="mean",
    t_start=1.6e-3,
    t_end=2.0e-3,
)
print(f"{name}: V(out) mean = {value.value:.4f}")
