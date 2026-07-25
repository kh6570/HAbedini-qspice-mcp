"""Measure several signals near the end of the extended half-bridge run."""

from __future__ import annotations

import sys
from pathlib import Path

from qspice_mcp.services.waveform.measure_waveform import measure_waveform

WS = Path(__file__).resolve().parent / "ws_build"

name = sys.argv[1]
t0, t1 = float(sys.argv[2]), float(sys.argv[3])
for sig in sys.argv[4:]:
    value = measure_waveform(
        f"{name}.qraw",
        workspace_root=WS,
        signal=sig,
        operation="mean",
        t_start=t0,
        t_end=t1,
    )
    print(f"{sig}: mean[{t0},{t1}] = {value.value:.4f}")
