"""Explore pin geometry and netlist node order for authoring primitives."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.read_component_symbol import read_component_symbol

WS = Path(__file__).resolve().parent / "ws_explore"
WS.mkdir(exist_ok=True)
settings = QSpiceSettings(workspace_root=WS)

sch = "probe.qsch"
create_schematic(sch, workspace_root=WS, overwrite=True)

parts = [
    ("resistor", "R1", "1k", 0),
    ("resistor", "R2", "1k", 90),
    ("capacitor", "C1", "1u", 0),
    ("inductor", "L1", "1u", 0),
    ("inductor", "L2", "1u", 90),
    ("diode", "D1", "DID", 0),
    ("diode", "D2", "DID", 90),
    ("voltage_source", "V1", "48", 0),
    ("nmos", "M1", "NSW", 0),
    ("behavioral", "B1", "V=V(a)", 0),
]
x = 0
for kind, ref, value, rot in parts:
    add_component(
        sch,
        workspace_root=WS,
        component_kind=kind,
        reference=ref,
        value=value,
        position_x=x,
        position_y=0,
        rotation_degrees=rot,
    )
    x += 1000

for _, ref, _, rot in parts:
    symbol = read_component_symbol(sch, workspace_root=WS, reference=ref)
    pins = [(pin.name, pin.position_x, pin.position_y) for pin in symbol.pins]
    print(f"{ref} rot={rot}: pins={pins}")
