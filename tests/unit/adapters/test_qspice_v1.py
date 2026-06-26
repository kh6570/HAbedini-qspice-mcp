"""Tests for the current QSpice CLI adapter command builder."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.adapters.cli.qspice_v1 import (
    LOG_CLASSIFICATION_VERSION,
    CurrentQSpiceCLIAdapter,
)
from qspice_mcp.adapters.probe import ProbeResult
from qspice_mcp.core.exceptions import ConvergenceError, SimulationError

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


# ---------------------------------------------------------------------------
# Log-classification contract
# ---------------------------------------------------------------------------


def test_log_classification_version_is_pinned() -> None:
    adapter = CurrentQSpiceCLIAdapter()

    assert adapter.log_classification_version == LOG_CLASSIFICATION_VERSION
    assert LOG_CLASSIFICATION_VERSION == 1


def test_classify_clean_log_returns_none() -> None:
    adapter = CurrentQSpiceCLIAdapter()

    result = adapter.classify_simulation_log(
        "Total elapsed time: 0.5 seconds\n100% complete\n",
        exit_code=0,
    )

    assert result is None


@pytest.mark.parametrize(
    "log_line",
    [
        "Internal timestep too small",
        "Timestep too small",
        "Failed to converge",
        "No convergence in DC analysis",
        "Convergence problem detected",
        "Iteration limit reached",
        "Singular matrix detected",
        "Trouble with node N001",
    ],
)
def test_classify_convergence_failures(log_line: str) -> None:
    adapter = CurrentQSpiceCLIAdapter()

    result = adapter.classify_simulation_log(log_line, exit_code=1, stderr="boom")

    assert isinstance(result, ConvergenceError)
    assert result.exit_code == 1
    assert "boom" in (result.stderr or "")


def test_classify_fatal_error_returns_simulation_error() -> None:
    adapter = CurrentQSpiceCLIAdapter()

    result = adapter.classify_simulation_log("Fatal error: missing model", exit_code=2)

    assert isinstance(result, SimulationError)
    assert not isinstance(result, ConvergenceError)
    assert result.exit_code == 2


def test_classify_prefers_convergence_over_fatal_on_same_line() -> None:
    adapter = CurrentQSpiceCLIAdapter()
    # A single line that satisfies both the fatal (^error) and convergence
    # patterns must be classified as the more specific convergence failure.
    result = adapter.classify_simulation_log("Error: internal timestep too small", exit_code=1)

    assert isinstance(result, ConvergenceError)


def test_supports_probe_version_is_permissive_baseline() -> None:
    adapter = CurrentQSpiceCLIAdapter()

    assert adapter.supports_probe_version(None) is True
    assert adapter.supports_probe_version("2024.07") is True
