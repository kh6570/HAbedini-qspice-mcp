"""Tests for the bounded generate_netlist service."""

from __future__ import annotations

import importlib
import os
from importlib.resources import files
from pathlib import Path

import pytest

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services.simulation.generate_netlist import GeneratedNetlist, generate_netlist

generate_netlist_service = importlib.import_module(
    "qspice_mcp.services.simulation.generate_netlist"
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
COMPARATOR_QSCH_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "schematics" / "comparator-test.qsch"


def _buck_schematic_bytes() -> bytes:
    return (
        files("qspice_mcp.data.recipes")
        / "non_isolated_dc_dc"
        / "buck_converter_cpp"
        / "Buck-converter.qsch"
    ).read_bytes()


def _fake_qux_generated_netlist(
    schematic_path: Path,
    destination: Path,
    *,
    settings: object,
) -> GeneratedNetlist:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        "\n".join(
            (
                f"* {schematic_path.name}",
                "X1 out clk 0 0 0 y Buck_controller",
                "V3 in 0 10",
                ".tran 0 300u",
                ".end",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    return GeneratedNetlist(
        source_path=schematic_path,
        netlist_path=destination,
        source_kind="schematic",
        refreshed=True,
        copied=False,
        netlist_backend="qux",
        warnings=(
            "Generated a derived netlist from the schematic via companion QUX.exe -Netlist.",
        ),
    )


def test_generate_netlist_returns_existing_sidecar_for_schematic(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    derived = tmp_path / "demo.net"
    derived.write_text("* derived\n", encoding="utf-8")
    os.utime(schematic, (1_000_000_000, 1_000_000_000))
    os.utime(derived, (2_000_000_000, 2_000_000_000))

    result = generate_netlist(schematic, workspace_root=tmp_path)

    assert result.source_kind == "schematic"
    assert result.netlist_path == derived.resolve()
    assert result.copied is False
    assert result.refreshed is False
    assert "existing derived netlist" in result.warnings[0].lower()


def test_generate_netlist_can_stage_a_netlist_copy(tmp_path: Path) -> None:
    netlist = tmp_path / "demo.cir"
    netlist.write_text("* demo\n", encoding="utf-8")
    destination = tmp_path / "artifacts" / "copied.net"

    result = generate_netlist(netlist, workspace_root=tmp_path, output_path=destination)

    assert result.source_kind == "netlist"
    assert result.netlist_path == destination.resolve(strict=False)
    assert result.copied is True
    assert destination.read_text(encoding="utf-8") == "* demo\n"


def test_generate_netlist_generates_from_schematic_via_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")
    destination = tmp_path / "artifacts" / "generated.net"

    class FakeQschEditor:
        def __init__(self, path: str) -> None:
            self.path = Path(path)

        def save_netlist(self, path: str) -> None:
            assert self.path == schematic.resolve(strict=False)
            Path(path).write_text("* generated\n", encoding="utf-8")

    monkeypatch.setattr(
        generate_netlist_service,
        "_load_qsch_editor_factory",
        lambda: (FakeQschEditor, "fake-backend"),
    )

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)

    assert result.source_kind == "schematic"
    assert result.netlist_path == destination.resolve(strict=False)
    assert result.refreshed is True
    assert result.copied is False
    assert destination.read_text(encoding="utf-8") == "* generated\n"
    assert "fake-backend.qscheditor" in result.warnings[0].lower()


def test_generate_netlist_generates_from_supported_qsch_via_clean_room_parser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(COMPARATOR_QSCH_FIXTURE.read_bytes())
    destination = tmp_path / "artifacts" / "generated.net"

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.source_kind == "schematic"
    assert result.netlist_path == destination.resolve(strict=False)
    assert result.refreshed is True
    assert result.copied is False
    assert "clean-room" in result.warnings[0].lower()
    assert "V1 in 0 sin 0 1 1K" in generated
    assert "V2 N01 0 0.95" in generated
    assert "X1 in N01 out COMPARATOR Vhigh=1 Vlow=0" in generated
    assert ".tran 5m" in generated
    assert generated.rstrip().endswith(".end")


def test_generate_netlist_clean_room_parser_handles_rotated_pins_and_micro_units(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "buck.qsch"
    schematic.write_bytes(_buck_schematic_bytes())
    destination = tmp_path / "artifacts" / "buck.net"

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))
    monkeypatch.setattr(
        generate_netlist_service, "_try_generate_netlist_with_qux", lambda *_a, **_k: None
    )

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.refreshed is True
    assert result.netlist_backend == "clean_room"
    assert "M1 in G S S BSC123N08NS3" in generated
    assert "L1 S N02 50u" in generated
    assert "C1 out N01 10u" in generated
    assert ".lib NMOS.txt" in generated
    assert ".lib Diode.txt" in generated
    assert ".tran 0 300u" in generated
    assert "X1 " not in generated
    assert any("clean-room parser omits" in warning for warning in result.warnings)


def test_generate_netlist_clean_room_parser_handles_mirrored_components(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "mirrored.qsch"
    schematic.write_text(
        "\n".join(
            (
                "schematic",
                "  component (200,200) 0 1",
                "    symbol Comparator",
                "    type: X",
                '    text (0,0) 1 0 0 0x0 -1 -1 "X1"',
                '    text (0,100) 1 0 0 0x0 -1 -1 "MIRRORAMP"',
                '    text (0,200) 1 0 0 0x0 -1 -1 "gain=4"',
                '    pin (-200,0) (-200,0) 1 0 0 0x0 -1 -1 "IN"',
                '    pin (200,-100) (200,-100) 1 0 0 0x0 -1 -1 "OUT"',
                '    pin (200,100) (200,100) 1 0 0 0x0 -1 -1 "REF"',
                '  net (400,200) 1 0 0 "VIN"',
                '  net (0,100) 1 0 0 "VOUT"',
                '  net (0,300) 1 0 0 "VREF"',
                '  text (0,0) 1 0 0 0x0 -1 -1 ".tran 1m"',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "artifacts" / "mirrored.net"

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.refreshed is True
    assert "X1 VIN VOUT VREF MIRRORAMP gain=4" in generated
    assert ".tran 1m" in generated


def test_generate_netlist_clean_room_parser_keeps_inductor_coupling_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "coupled.qsch"
    schematic.write_text(
        "\n".join(
            (
                "schematic",
                "  component (0,0) 0 0",
                "    symbol ind",
                "    type: L",
                '    text (0,0) 1 0 0 0x0 -1 -1 "L1"',
                '    text (0,100) 1 0 0 0x0 -1 -1 "2m"',
                '    pin (0,200) (0,200) 1 0 0 0x0 -1 -1 "1"',
                '    pin (0,-200) (0,-200) 1 0 0 0x0 -1 -1 "2"',
                "  component (600,0) 0 0",
                "    symbol ind",
                "    type: L",
                '    text (0,0) 1 0 0 0x0 -1 -1 "L2"',
                '    text (0,100) 1 0 0 0x0 -1 -1 "500u"',
                '    pin (0,200) (0,200) 1 0 0 0x0 -1 -1 "1"',
                '    pin (0,-200) (0,-200) 1 0 0 0x0 -1 -1 "2"',
                '  net (0,200) 1 0 0 "a"',
                '  net (0,-200) 1 0 0 "0"',
                '  net (600,200) 1 0 0 "b"',
                '  net (600,-200) 1 0 0 "0"',
                '  text (0,500) 1 0 0 0x0 -1 -1 "K1 L1 L2 1"',
                '  text (0,600) 1 0 0 0x0 -1 -1 "plain annotation text"',
                '  text (0,700) 1 0 0 0x0 -1 -1 ".tran 1m"',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "artifacts" / "coupled.net"

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.refreshed is True
    assert "K1 L1 L2 1" in generated
    assert "plain annotation text" not in generated
    assert ".tran 1m" in generated


def test_generate_netlist_clean_room_parser_handles_nested_hierarchy_blocks_and_reordered_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "hierarchy.qsch"
    schematic.write_text(
        "\n".join(
            (
                "schematic",
                "  component (0,0) 0 0",
                "    symbol HierBlock",
                "    type: X",
                '    pin (-100,0) (-100,0) 1 0 0 0x0 -1 -1 "in"',
                '    pin (100,0) (100,0) 1 0 0 0x0 -1 -1 "out"',
                "    component (300,0) 0 0",
                "      symbol Amplifier",
                "      type: X",
                '      text (0,200) 1 0 0 0x0 -1 -1 "gain=2"',
                '      text (0,0) 1 0 0 0x0 -1 -1 "X1"',
                '      text (0,100) 1 0 0 0x0 -1 -1 "AMP"',
                '      text (0,300) 1 0 0 0x0 -1 -1 "mode=fast"',
                '      pin (-100,0) (-100,0) 1 0 0 0x0 -1 -1 "in"',
                '      pin (100,0) (100,0) 1 0 0 0x0 -1 -1 "out"',
                '  net (200,0) 1 0 0 "VIN"',
                '  net (400,0) 1 0 0 "VOUT"',
                '  text (0,0) 1 0 0 0x0 -1 -1 ".tran 2m"',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    destination = tmp_path / "artifacts" / "hierarchy.net"

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.refreshed is True
    assert "X1 VIN VOUT AMP gain=2 mode=fast" in generated
    assert "HierBlock" not in generated
    assert ".tran 2m" in generated


def test_generate_netlist_regenerates_when_schematic_is_newer_than_sidecar(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(COMPARATOR_QSCH_FIXTURE.read_bytes())
    derived = tmp_path / "demo.net"
    derived.write_text("* stale derived\n", encoding="utf-8")
    os.utime(derived, (1_000_000_000, 1_000_000_000))
    os.utime(schematic, (2_000_000_000, 2_000_000_000))

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    result = generate_netlist(schematic, workspace_root=tmp_path)

    assert result.refreshed is True
    assert "clean-room" in result.warnings[0].lower()
    assert "stale derived" not in derived.read_text(encoding="utf-8")
    assert "V1 in 0 sin 0 1 1K" in derived.read_text(encoding="utf-8")


def test_generate_netlist_raises_when_schematic_has_no_sidecar_or_editor_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_text("schematic", encoding="utf-8")

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))

    with pytest.raises(QSpiceError, match=r"QschEditor backend is installed"):
        generate_netlist(schematic, workspace_root=tmp_path)


def test_generate_netlist_prefers_qux_for_dll_schematic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "buck.qsch"
    schematic.write_bytes(_buck_schematic_bytes())
    destination = tmp_path / "artifacts" / "buck.net"

    monkeypatch.setattr(
        generate_netlist_service,
        "_try_generate_netlist_with_qux",
        _fake_qux_generated_netlist,
    )

    result = generate_netlist(schematic, workspace_root=tmp_path, output_path=destination)
    generated = destination.read_text(encoding="utf-8")

    assert result.refreshed is True
    assert result.netlist_backend == "qux"
    assert "X1 out clk 0 0 0 y Buck_controller" in generated
    assert any("qux.exe -netlist" in warning.lower() for warning in result.warnings)


def test_generate_netlist_refreshes_incomplete_dll_sidecar_even_when_not_stale(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "buck.qsch"
    schematic.write_bytes(_buck_schematic_bytes())
    derived = tmp_path / "buck.net"
    derived.write_text("* incomplete\nV3 in 0 10\n.end\n", encoding="utf-8")
    os.utime(schematic, (2_000_000_000, 2_000_000_000))
    os.utime(derived, (3_000_000_000, 3_000_000_000))

    monkeypatch.setattr(
        generate_netlist_service,
        "_try_generate_netlist_with_qux",
        _fake_qux_generated_netlist,
    )

    result = generate_netlist(schematic, workspace_root=tmp_path)

    assert result.refreshed is True
    assert result.netlist_backend == "qux"
    assert "X1 out clk 0 0 0 y Buck_controller" in derived.read_text(encoding="utf-8")


def test_generate_netlist_dll_schematic_without_qux_warns_about_omission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    schematic = tmp_path / "buck.qsch"
    schematic.write_bytes(_buck_schematic_bytes())

    monkeypatch.setattr(generate_netlist_service, "_load_qsch_editor_factory", lambda: (None, None))
    monkeypatch.setattr(
        generate_netlist_service, "_try_generate_netlist_with_qux", lambda *_a, **_k: None
    )

    result = generate_netlist(schematic, workspace_root=tmp_path)

    assert result.refreshed is True
    assert result.netlist_backend == "clean_room"
    assert any("clean-room parser omits" in warning for warning in result.warnings)
