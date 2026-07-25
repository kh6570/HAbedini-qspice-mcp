"""Probe QUX netlist node ordering for authoring primitives."""

from __future__ import annotations

import shutil
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.add_instruction import add_instruction
from qspice_mcp.services.schematic.add_net_label import add_net_label
from qspice_mcp.services.schematic.add_wire import add_wire
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.simulation.generate_netlist import generate_netlist

WS = Path(__file__).resolve().parent / "ws_probe"
if WS.exists():
    shutil.rmtree(WS)
WS.mkdir(parents=True)
settings = QSpiceSettings(workspace_root=WS)

sch = "probe.qsch"
create_schematic(sch, workspace_root=WS, overwrite=True)


def add(kind: str, ref: str, value: str, x: int, y: int, rot: int = 0) -> None:
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


# Column layout, each part vertical at rotation 0; pin1/top at (x, y+200).
add("voltage_source", "V1", "48", 0, 0)
add("resistor", "R1", "10", 1000, 0)
add("inductor", "L1", "1u", 2000, 0)
add("diode", "D1", "DID", 3000, 0)
add("capacitor", "C1", "1u", 4000, 0)
add("nmos", "M1", "NSW", 5000, 0)
add("ground", "G1", "", 0, -1000)

# Tie every top pin to net "top", every bottom pin to net "bot" via labeled wires.


def wire_pin(ref: str, pin: str, net: str, dx: int, dy: int) -> None:
    add_wire(
        sch,
        workspace_root=WS,
        start_reference=ref,
        start_pin=pin,
        end_x=None,
        end_y=None,
        net_name=net,
    )


# add_wire with only start anchors may need explicit ends; use pin-to-pin instead.
add_wire(sch, workspace_root=WS, start_reference="V1", start_pin="+", end_reference="R1", end_pin="1", net_name="top")
add_wire(sch, workspace_root=WS, start_reference="R1", start_pin="1", end_reference="L1", end_pin="1", net_name="top")
add_wire(sch, workspace_root=WS, start_reference="L1", start_pin="1", end_reference="D1", end_pin="A", net_name="top")
add_wire(sch, workspace_root=WS, start_reference="D1", start_pin="A", end_reference="C1", end_pin="+", net_name="top")
add_wire(sch, workspace_root=WS, start_reference="C1", start_pin="+", end_reference="M1", end_pin="D", net_name="top")
add_wire(sch, workspace_root=WS, start_reference="V1", start_pin="-", end_reference="R1", end_pin="2", net_name="GND")
add_wire(sch, workspace_root=WS, start_reference="R1", start_pin="2", end_reference="L1", end_pin="2", net_name="GND")
add_wire(sch, workspace_root=WS, start_reference="L1", start_pin="2", end_reference="D1", end_pin="K", net_name="GND")
add_wire(sch, workspace_root=WS, start_reference="D1", start_pin="K", end_reference="C1", end_pin="-", net_name="GND")
add_wire(sch, workspace_root=WS, start_reference="C1", start_pin="-", end_reference="M1", end_pin="S", net_name="GND")
add_wire(sch, workspace_root=WS, start_reference="M1", start_pin="G", end_reference="M1", end_pin="S", net_name="GND")
# Ground the bottom rail: wire V1(-) down to the ground symbol position.
add_wire(sch, workspace_root=WS, start_reference="V1", start_pin="-", end_x=0, end_y=-1000, net_name="GND")

add_instruction(sch, workspace_root=WS, instruction=".model NSW NMOS(Vto=2 Kp=10)")
add_instruction(sch, workspace_root=WS, instruction=".model DID D(Ron=10m Vfwd=0.4)")
add_instruction(sch, workspace_root=WS, instruction=".tran 0 1u")

result = generate_netlist(sch, workspace_root=WS, settings=settings)
print("netlist:", result.netlist_path)
print(result.netlist_path.read_text(encoding="utf-8", errors="replace"))
