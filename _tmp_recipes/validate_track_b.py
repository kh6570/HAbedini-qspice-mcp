"""End-to-end Track-B validation for the three new bundled recipes."""

from __future__ import annotations

import shutil
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.schematic.materialize_reference_circuit import (
    materialize_reference_circuit,
)
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.measure_waveform import measure_waveform

WS = Path(__file__).resolve().parent / "ws_trackb"

CASES = [
    ("forward_converter", 8.5, 10.0),
    ("half_bridge_converter", 7.0, 8.8),
    ("full_bridge_converter", 7.0, 8.8),
]

if WS.exists():
    shutil.rmtree(WS)
WS.mkdir(parents=True)

settings = QSpiceSettings(workspace_root=WS)
for recipe_id, lo, hi in CASES:
    materialized = materialize_reference_circuit(recipe_id, workspace_root=WS)
    names = [Path(f.output_path).name for f in materialized.files]
    print(f"{recipe_id}: materialized {names}")
    run = run_simulation(
        f"{recipe_id}.cir", workspace_root=WS, settings=settings, timeout_s=240
    )
    measured = measure_waveform(
        run.raw_path,
        workspace_root=WS,
        signal="V(out)",
        operation="mean",
        t_start=1.6e-3,
        t_end=2.0e-3,
    )
    status = "OK" if lo <= measured.value <= hi else "FAIL"
    print(f"{recipe_id}: exit={run.exit_code} V(out)={measured.value:.4f} [{lo},{hi}] {status}")
    if status == "FAIL":
        raise SystemExit(1)
print("TRACK B ALL OK")
