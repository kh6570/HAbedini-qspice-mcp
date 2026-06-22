"""Rebuild the desktop RLC filter demo with wide collision-aware spacing."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.services._backends.schematic_editor import (
    open_schematic_editor,
    resolve_component_pin_position,
)
from qspice_mcp.services.schematic.add_component import add_component
from qspice_mcp.services.schematic.add_net_label import add_net_label
from qspice_mcp.services.schematic.add_wire import add_wire
from qspice_mcp.services.schematic.create_schematic import create_schematic
from qspice_mcp.services.schematic.read_component import read_component
from qspice_mcp.services.schematic.suggest_component_placement import suggest_component_placement
from qspice_mcp.services.simulation.generate_netlist import generate_netlist
from qspice_mcp.services.simulation.prepare_transient import prepare_transient
from qspice_mcp.services.simulation.run_simulation import run_simulation


def main() -> None:
    workspace = Path(r"C:\Users\habed\Desktop\qspice-mcp-test")
    schematic = workspace / "rlc_filter.qsch"
    create_schematic(schematic, workspace_root=workspace, overwrite=True)

    for kind, reference, value in (
        ("voltage_source", "V1", "PULSE(0 5 0 1n 1n 5u 10u)"),
        ("resistor", "R1", "100"),
        ("inductor", "L1", "1m"),
        ("capacitor", "C1", "1u"),
    ):
        suggestion = suggest_component_placement(
            schematic,
            workspace_root=workspace,
            component_kind=kind,
        )
        add_component(
            schematic,
            workspace_root=workspace,
            component_kind=kind,
            reference=reference,
            value=value,
            position_x=suggestion.position_x,
            position_y=suggestion.position_y,
            rotation_degrees=0,
        )

    add_wire(
        schematic,
        workspace_root=workspace,
        net_name="VIN",
        start_reference="V1",
        start_pin="+",
        end_reference="R1",
        end_pin="1",
    )
    add_wire(
        schematic,
        workspace_root=workspace,
        net_name="N001",
        start_reference="R1",
        start_pin="2",
        end_reference="L1",
        end_pin="1",
    )
    add_wire(
        schematic,
        workspace_root=workspace,
        net_name="VOUT",
        start_reference="L1",
        start_pin="2",
        end_reference="C1",
        end_pin="+",
    )

    editor, _, _ = open_schematic_editor(schematic, workspace_root=workspace)
    for reference, pin in (("V1", "-"), ("C1", "-")):
        pin_x, pin_y = resolve_component_pin_position(
            editor,
            reference=reference,
            pin_name=pin,
        )
        add_component(
            schematic,
            workspace_root=workspace,
            component_kind="ground",
            position_x=pin_x,
            position_y=pin_y,
            rotation_degrees=0,
            net_name="0",
        )

    c1 = read_component(schematic, workspace_root=workspace, reference="C1")
    add_net_label(
        schematic,
        workspace_root=workspace,
        net_name="VOUT",
        position_x=c1.position_x + 100,
        position_y=c1.position_y - 40,
    )

    staged = prepare_transient(
        schematic,
        workspace_root=workspace,
        step="100n",
        stop="100u",
    )
    netlist = generate_netlist(staged.output_path, workspace_root=workspace)
    result = run_simulation(netlist.netlist_path, workspace_root=workspace)
    print(netlist.netlist_path.read_text(encoding="utf-8"))
    print(f"sim exit_code={result.exit_code}")
    print(f"built {schematic}")


if __name__ == "__main__":
    main()
