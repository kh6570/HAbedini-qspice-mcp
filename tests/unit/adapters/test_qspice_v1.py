"""Tests for the current QSpice CLI adapter command builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.adapters.cli.qspice_v1 import CurrentQSpiceCLIAdapter
from qspice_mcp.adapters.probe import ProbeResult

if TYPE_CHECKING:
    from pathlib import Path


def _make_probe(executable: Path) -> ProbeResult:
    executable.write_text("", encoding="utf-8")
    return ProbeResult(
        configured=True,
        executable=executable.resolve(),
        exists=True,
        source="configured",
    )


def test_build_simulation_command_uses_default_artifacts(tmp_path: Path) -> None:
    adapter = CurrentQSpiceCLIAdapter()
    probe = _make_probe(tmp_path / "QSPICE64.exe")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    command = adapter.build_simulation_command(probe, netlist)

    normalized_netlist = netlist.resolve()
    assert command.command == (
        str(probe.executable),
        "-o",
        str(normalized_netlist.with_suffix(".log")),
        str(normalized_netlist),
    )
    assert command.working_directory == normalized_netlist.parent
    assert command.netlist_file == normalized_netlist
    assert command.log_file == normalized_netlist.with_suffix(".log")
    assert command.raw_file == normalized_netlist.with_suffix(".qraw")


def test_build_simulation_command_supports_custom_outputs_and_switches(tmp_path: Path) -> None:
    adapter = CurrentQSpiceCLIAdapter()
    probe = _make_probe(tmp_path / "QSPICE64.exe")
    netlist = tmp_path / "demo.cir"
    netlist.write_text("* demo\n", encoding="utf-8")
    log_file = tmp_path / "artifacts" / "run.log"
    raw_file = tmp_path / "artifacts" / "run.qraw"

    command = adapter.build_simulation_command(
        probe,
        netlist,
        log_file=log_file,
        raw_file=raw_file,
        ascii_raw=True,
        extra_switches=("-BSIM1", "-Meyer"),
    )

    assert command.command == (
        str(probe.executable),
        "-o",
        str(log_file.resolve(strict=False)),
        str(netlist.resolve()),
        "-r",
        str(raw_file.resolve(strict=False)),
        "-ASCII",
        "-BSIM1",
        "-Meyer",
    )
    assert command.log_file == log_file.resolve(strict=False)
    assert command.raw_file == raw_file.resolve(strict=False)


def test_build_simulation_command_rejects_schematic_inputs(tmp_path: Path) -> None:
    adapter = CurrentQSpiceCLIAdapter()
    probe = _make_probe(tmp_path / "QSPICE64.exe")
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("placeholder", encoding="utf-8")

    with pytest.raises(ValueError, match=r"\.cir or \.net"):
        adapter.build_simulation_command(probe, schematic)


def test_build_simulation_command_rejects_reserved_output_switches(tmp_path: Path) -> None:
    adapter = CurrentQSpiceCLIAdapter()
    probe = _make_probe(tmp_path / "QSPICE64.exe")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    with pytest.raises(ValueError, match="managed by the adapter"):
        adapter.build_simulation_command(probe, netlist, extra_switches=("-o", "other.log"))


def test_build_simulation_command_rejects_positional_or_pathlike_switches(tmp_path: Path) -> None:
    adapter = CurrentQSpiceCLIAdapter()
    probe = _make_probe(tmp_path / "QSPICE64.exe")
    netlist = tmp_path / "demo.net"
    netlist.write_text("* demo\n", encoding="utf-8")

    with pytest.raises(ValueError, match="dash-prefixed flags"):
        adapter.build_simulation_command(probe, netlist, extra_switches=("other.log",))

    with pytest.raises(ValueError, match="path-like values"):
        adapter.build_simulation_command(
            probe,
            netlist,
            extra_switches=(r"-Config=C:\temp\outside.cfg",),
        )
