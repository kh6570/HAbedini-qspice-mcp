"""Author the forward / half-bridge / full-bridge clean-room recipe schematics.

Builds each `.qsch` with qspice-mcp authoring services only, verifies net
connectivity, generates the netlist, runs the local QSpice, and checks the
steady-state V(out) against the blueprint design value.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services._backends.schematic_editor import open_schematic_editor
from qspice_mcp.services._backends.schematic_editor_geometry import (
    resolve_component_pin_position,
)
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.add_instruction import add_instruction
from qspice_mcp.services.schematic.add_wire import add_wire
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.read_net_connectivity import read_net_connectivity
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.run_simulation import run_simulation
from qspice_mcp.services.waveform.measure_waveform import measure_waveform

WS = Path(__file__).resolve().parent / "ws_build"

# (kind, ref, value, x, y, rot)
Part = tuple[str, str, str, int, int, int]
# (ref, pin, net)
Bind = tuple[str, str, str]

STUB = 200


def build(name: str, parts: list[Part], binds: list[Bind], instructions: list[str]) -> Path:
    sch = f"{name}.qsch"
    settings = QSpiceSettings(workspace_root=WS)
    create_schematic(sch, workspace_root=WS, overwrite=True)
    for kind, ref, value, x, y, rot in parts:
        add_component(
            sch,
            workspace_root=WS,
            component_kind=kind,
            reference=ref,
            value=value,
            position_x=x,
            position_y=y,
            rotation_degrees=rot,
        )

    editor, _, _ = open_schematic_editor(sch, workspace_root=WS)
    centers = {ref: (x, y) for _, ref, _, x, y, _ in parts}
    pin_positions: dict[tuple[str, str], tuple[int, int]] = {}
    for ref, pin, _ in binds:
        pin_positions[(ref, pin)] = resolve_component_pin_position(
            editor, reference=ref, pin_name=pin
        )

    for ref, pin, net in binds:
        px, py = pin_positions[(ref, pin)]
        cx, cy = centers[ref]
        dx, dy = px - cx, py - cy
        if abs(dy) >= abs(dx):
            ex, ey = px, py + (STUB if dy >= 0 else -STUB)
        else:
            ex, ey = px + (STUB if dx >= 0 else -STUB), py
        add_wire(
            sch,
            workspace_root=WS,
            start_reference=ref,
            start_pin=pin,
            end_x=ex,
            end_y=ey,
            net_name=net,
        )

    for instruction in instructions:
        add_instruction(sch, workspace_root=WS, instruction=instruction)

    report = read_net_connectivity(WS / sch, workspace_root=WS)
    print(f"--- {name}: nets ---")
    for net in report.nets:
        print(f"  {net.net}: {[f'{p.reference}.{p.pin}' for p in net.pins]}")

    netlist = generate_netlist(sch, workspace_root=WS, settings=QSpiceSettings(workspace_root=WS))
    print(f"--- {name}: netlist ---")
    print(netlist.netlist_path.read_text(encoding="utf-8", errors="replace"))
    return WS / sch


def simulate_and_check(name: str, lo: float, hi: float) -> None:
    settings = QSpiceSettings(workspace_root=WS)
    run = run_simulation(f"{name}.net", workspace_root=WS, settings=settings, timeout_s=240)
    print(f"{name}: exit={run.exit_code} raw={run.raw_path}")
    measured = measure_waveform(
        run.raw_path,
        workspace_root=WS,
        signal="V(out)",
        operation="mean",
        t_start=1.6e-3,
        t_end=2.0e-3,
    )
    print(f"{name}: V(out) mean over [1.6m,2m] = {measured.value:.4f} (expect {lo}..{hi})")
    if not (lo <= measured.value <= hi):
        raise SystemExit(f"{name}: V(out)={measured.value} outside [{lo},{hi}]")


MODELS = [
    ".model NSW NMOS(Vto=2 Kp=10)",
    ".model DID D(Ron=10m Vfwd=0.4 Epsilon=0.05 Revepsilon=0.05)",
]
TRAN = ".tran 0 2m 0 200n"


def forward() -> None:
    # Vin=48, n=0.5, n31=1, D=0.4, fsw=100k -> Vout ~ 9.2 V after diode drops.
    parts: list[Part] = [
        ("voltage_source", "V1", "48", -3200, 800, 0),
        ("voltage_source", "V2", "pulse 0 15 0 20n 20n 4u 10u", -2000, -800, 0),
        ("nmos", "M1", "NSW", -800, -800, 0),
        ("inductor", "L2", "2m", -800, 800, 0),  # primary, dot=pin1 top -> in
        ("inductor", "L4", "2m", -2000, 800, 0),  # reset winding, dot=pin1 top -> rst
        ("inductor", "L3", "500u", 400, 800, 0),  # secondary, dot=pin1 top -> sec
        ("diode", "D3", "DID", -2600, 800, 0),  # reset diode, A=bottom, K=top
        ("diode", "D1", "DID", 1000, 800, 0),  # forward rectifier
        ("diode", "D2", "DID", 1600, 800, 0),  # freewheel
        ("inductor", "L1", "100u", 2200, 800, 0),  # output filter
        ("capacitor", "C1", "47u", 2800, 800, 0),
        ("resistor", "R1", "5", 3400, 800, 0),
    ]
    binds: list[Bind] = [
        ("V1", "+", "in"),
        ("V1", "-", "GND"),
        ("V2", "+", "g"),
        ("V2", "-", "GND"),
        ("M1", "D", "sw"),
        ("M1", "G", "g"),
        ("M1", "S", "GND"),
        ("L2", "1", "in"),
        ("L2", "2", "sw"),
        ("L4", "1", "rst"),
        ("L4", "2", "in"),
        ("D3", "A", "GND"),
        ("D3", "K", "rst"),
        ("L3", "1", "sec"),
        ("L3", "2", "GND"),
        ("D1", "A", "sec"),
        ("D1", "K", "x1"),
        ("D2", "A", "GND"),
        ("D2", "K", "x1"),
        ("L1", "1", "x1"),
        ("L1", "2", "out"),
        ("C1", "+", "out"),
        ("C1", "-", "GND"),
        ("R1", "1", "out"),
        ("R1", "2", "GND"),
    ]
    instructions = [*MODELS, "K1 L2 L3 L4 1", TRAN]
    build("forward_converter", parts, binds, instructions)
    simulate_and_check("forward_converter", 8.5, 10.0)


def half_bridge() -> None:
    # Vin=48, n=1, D=0.35 (t_on per switch 1.75u of 10u) -> Vout ~ 7.6 V.
    parts: list[Part] = [
        ("voltage_source", "V1", "48", -4400, 800, 0),
        ("capacitor", "CB1", "10u", -3400, 1400, 0),
        ("capacitor", "CB2", "10u", -3400, 200, 0),
        ("resistor", "RB1", "10k", -2800, 1400, 0),
        ("resistor", "RB2", "10k", -2800, 200, 0),
        ("nmos", "M1", "NSW", -1600, 1400, 0),
        ("nmos", "M2", "NSW", -1600, 200, 0),
        ("voltage_source", "VG1", "pulse 0 15 0 20n 20n 2u 10u", -600, 1400, 0),
        ("voltage_source", "VG2", "pulse 0 15 5u 20n 20n 2u 10u", -600, 200, 0),
        ("diode", "DA1", "DID", -2200, 1400, 0),
        ("diode", "DA2", "DID", -2200, 200, 0),
        ("inductor", "L2", "2m", -1000, -1200, 0),  # primary dot=pin1 -> swm
        ("inductor", "L3", "2m", 200, -1200, 0),  # secondary dot=pin1 -> s1
        ("resistor", "RS1", "1Meg", 800, -1200, 0),
        ("resistor", "RN1", "100", -1800, -2000, 0),  # primary RC snubber
        ("capacitor", "CN1", "10n", -400, -2600, 0),
        ("diode", "D1", "DID", 1400, 800, 0),
        ("diode", "D2", "DID", 2000, 800, 0),
        ("diode", "D3", "DID", 1400, -400, 0),
        ("diode", "D4", "DID", 2000, -400, 0),
        ("inductor", "L1", "100u", 2600, 800, 0),
        ("capacitor", "C1", "47u", 3200, 800, 0),
        ("resistor", "R1", "3.5", 3800, 800, 0),
    ]
    binds: list[Bind] = [
        ("V1", "+", "in"),
        ("V1", "-", "GND"),
        ("CB1", "+", "in"),
        ("CB1", "-", "mid"),
        ("CB2", "+", "mid"),
        ("CB2", "-", "GND"),
        ("RB1", "1", "in"),
        ("RB1", "2", "mid"),
        ("RB2", "1", "mid"),
        ("RB2", "2", "GND"),
        ("M1", "D", "in"),
        ("M1", "G", "g1"),
        ("M1", "S", "swm"),
        ("M2", "D", "swm"),
        ("M2", "G", "g2"),
        ("M2", "S", "GND"),
        ("VG1", "+", "g1"),
        ("VG1", "-", "swm"),
        ("VG2", "+", "g2"),
        ("VG2", "-", "GND"),
        ("DA1", "A", "swm"),
        ("DA1", "K", "in"),
        ("DA2", "A", "GND"),
        ("DA2", "K", "swm"),
        ("L2", "1", "swm"),
        ("L2", "2", "mid"),
        ("RN1", "1", "swm"),
        ("RN1", "2", "sn"),
        ("CN1", "+", "sn"),
        ("CN1", "-", "mid"),
        ("L3", "1", "s1"),
        ("L3", "2", "s2"),
        ("RS1", "1", "s2"),
        ("RS1", "2", "GND"),
        ("D1", "A", "s1"),
        ("D1", "K", "xr"),
        ("D2", "A", "s2"),
        ("D2", "K", "xr"),
        ("D3", "A", "GND"),
        ("D3", "K", "s1"),
        ("D4", "A", "GND"),
        ("D4", "K", "s2"),
        ("L1", "1", "xr"),
        ("L1", "2", "out"),
        ("C1", "+", "out"),
        ("C1", "-", "GND"),
        ("R1", "1", "out"),
        ("R1", "2", "GND"),
    ]
    instructions = [*MODELS, "K1 L2 L3 0.9995", ".options reltol=1m", TRAN]
    build("half_bridge_converter", parts, binds, instructions)
    simulate_and_check("half_bridge_converter", 7.0, 8.8)


def full_bridge() -> None:
    # Vin=48, n=0.5, D=0.35 (t_on per pair 1.75u of 10u) -> Vout ~ 7.6 V.
    parts: list[Part] = [
        ("voltage_source", "V1", "48", -4400, 800, 0),
        ("nmos", "M1", "NSW", -2600, 1400, 0),
        ("nmos", "M4", "NSW", -2600, 200, 0),
        ("nmos", "M3", "NSW", -1200, 1400, 0),
        ("nmos", "M2", "NSW", -1200, 200, 0),
        ("voltage_source", "VG1", "pulse 0 15 0 20n 20n 1.75u 10u", -3600, 1400, 0),
        ("voltage_source", "VG4", "pulse 0 15 5u 20n 20n 1.75u 10u", -3600, 200, 0),
        ("voltage_source", "VG3", "pulse 0 15 5u 20n 20n 1.75u 10u", -200, 1400, 0),
        ("voltage_source", "VG2", "pulse 0 15 0 20n 20n 1.75u 10u", -200, 200, 0),
        ("diode", "DA1", "DID", -2000, 1400, 0),
        ("diode", "DA4", "DID", -2000, 200, 0),
        ("diode", "DA3", "DID", -600, 1400, 0),
        ("diode", "DA2", "DID", -600, 200, 0),
        ("resistor", "RB1", "100k", -1900, -1200, 0),
        ("inductor", "L2", "2m", -1300, -1200, 0),  # primary dot=pin1 -> swa
        ("inductor", "L3", "500u", 200, -1200, 0),  # secondary dot=pin1 -> s1
        ("resistor", "RS1", "1Meg", 800, -1200, 0),
        ("resistor", "RN1", "100", -2500, -2000, 0),  # primary RC snubber
        ("capacitor", "CN1", "10n", -700, -2600, 0),
        ("diode", "D1", "DID", 1400, 800, 0),
        ("diode", "D2", "DID", 2000, 800, 0),
        ("diode", "D3", "DID", 1400, -400, 0),
        ("diode", "D4", "DID", 2000, -400, 0),
        ("inductor", "L1", "100u", 2600, 800, 0),
        ("capacitor", "C1", "47u", 3200, 800, 0),
        ("resistor", "R1", "3.5", 3800, 800, 0),
    ]
    binds: list[Bind] = [
        ("V1", "+", "in"),
        ("V1", "-", "GND"),
        # Leg A: M1 high (in -> swa), M4 low (swa -> GND)
        ("M1", "D", "in"),
        ("M1", "G", "g1"),
        ("M1", "S", "swa"),
        ("M4", "D", "swa"),
        ("M4", "G", "g4"),
        ("M4", "S", "GND"),
        # Leg B: M3 high (in -> swb), M2 low (swb -> GND)
        ("M3", "D", "in"),
        ("M3", "G", "g3"),
        ("M3", "S", "swb"),
        ("M2", "D", "swb"),
        ("M2", "G", "g2"),
        ("M2", "S", "GND"),
        ("VG1", "+", "g1"),
        ("VG1", "-", "swa"),
        ("VG4", "+", "g4"),
        ("VG4", "-", "GND"),
        ("VG3", "+", "g3"),
        ("VG3", "-", "swb"),
        ("VG2", "+", "g2"),
        ("VG2", "-", "GND"),
        ("DA1", "A", "swa"),
        ("DA1", "K", "in"),
        ("DA4", "A", "GND"),
        ("DA4", "K", "swa"),
        ("DA3", "A", "swb"),
        ("DA3", "K", "in"),
        ("DA2", "A", "GND"),
        ("DA2", "K", "swb"),
        ("RB1", "1", "swb"),
        ("RB1", "2", "GND"),
        ("L2", "1", "swa"),
        ("L2", "2", "swb"),
        ("RN1", "1", "swa"),
        ("RN1", "2", "sn"),
        ("CN1", "+", "sn"),
        ("CN1", "-", "swb"),
        ("L3", "1", "s1"),
        ("L3", "2", "s2"),
        ("RS1", "1", "s2"),
        ("RS1", "2", "GND"),
        ("D1", "A", "s1"),
        ("D1", "K", "xr"),
        ("D2", "A", "s2"),
        ("D2", "K", "xr"),
        ("D3", "A", "GND"),
        ("D3", "K", "s1"),
        ("D4", "A", "GND"),
        ("D4", "K", "s2"),
        ("L1", "1", "xr"),
        ("L1", "2", "out"),
        ("C1", "+", "out"),
        ("C1", "-", "GND"),
        ("R1", "1", "out"),
        ("R1", "2", "GND"),
    ]
    instructions = [*MODELS, "K1 L2 L3 0.9995", ".options reltol=1m", TRAN]
    build("full_bridge_converter", parts, binds, instructions)
    simulate_and_check("full_bridge_converter", 7.0, 8.8)


if __name__ == "__main__":
    if WS.exists():
        shutil.rmtree(WS)
    WS.mkdir(parents=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "forward"):
        forward()
    if which in ("all", "half"):
        half_bridge()
    if which in ("all", "full"):
        full_bridge()
    print("ALL OK")
