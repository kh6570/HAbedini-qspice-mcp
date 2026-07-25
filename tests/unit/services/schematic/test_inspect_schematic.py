"""Tests for schematic inspection."""

from __future__ import annotations

import json
from pathlib import Path

from qspice_mcp.core.models import AnalysisKind
from qspice_mcp.mcp.tools.shared import to_json_object
from qspice_mcp.services._backends._qsch_editor import _decode_qsch_bytes
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic


def test_inspect_schematic_extracts_components_and_analyses(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(
        b"".join(
            (
                b"\xabschematic\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol V\r\n",
                b"      \xabtype: V\xbb\r\n",
                b"      \xabdescription: Independent Voltage Source\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "V1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "10"\xbb\r\n',
                b"    \xbb\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol R\r\n",
                b"      \xabtype: R\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "1k"\xbb\r\n',
                b"    \xbb\r\n",
                b'  \xabtext (0,0) 1 7 0 0x1000000 -1 -1 ".tran 5m"\xbb\r\n',
                b"\xbb\r\n",
            )
        )
    )

    summary = inspect_schematic(schematic, workspace_root=tmp_path)

    assert summary.title == "demo"
    assert summary.format_hint == "schematic"
    assert summary.component_count == 2
    assert summary.components[0].refdes == "V1"
    assert summary.components[0].value == "10"
    assert summary.components[1].kind == "R"
    assert summary.analyses[0].kind is AnalysisKind.TRAN
    assert summary.analyses[0].raw == ".tran 5m"


def test_inspect_schematic_truncates_component_rows_when_bounded(tmp_path: Path) -> None:
    schematic = tmp_path / "demo.qsch"
    schematic.write_bytes(
        b"".join(
            (
                b"\xabschematic\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol V\r\n",
                b"      \xabtype: V\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "V1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "10"\xbb\r\n',
                b"    \xbb\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol R\r\n",
                b"      \xabtype: R\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "1k"\xbb\r\n',
                b"    \xbb\r\n",
                b"\xbb\r\n",
            )
        )
    )

    summary = inspect_schematic(schematic, workspace_root=tmp_path, max_components=1)

    assert summary.component_count == 2
    assert len(summary.components) == 1
    assert summary.components[0].refdes == "V1"
    assert summary.components_truncated is True

    unbounded = inspect_schematic(schematic, workspace_root=tmp_path)
    assert unbounded.components_truncated is False
    assert len(unbounded.components) == 2


def test_inspect_schematic_decodes_latin1_qsch_bytes(tmp_path: Path) -> None:
    schematic = tmp_path / "latin1.qsch"
    schematic.write_bytes(
        b"".join(
            (
                b"\xff\xd8\xff\xdb",
                b"\xabschematic\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol V\r\n",
                b"      \xabtype: V\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "V1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "10"\xbb\r\n',
                b"    \xbb\r\n",
                b"  \xbb\r\n",
                b"\xbb\r\n\r\n",
            )
        )
    )

    summary = inspect_schematic(schematic, workspace_root=tmp_path)

    assert summary.format_hint == "schematic"
    assert summary.component_count == 1
    assert summary.components[0].refdes == "V1"
    assert summary.components[0].value == "10"


def test_decode_qsch_bytes_avoids_utf8_misdecode_of_latin1_guillemets() -> None:
    """Latin-1 guillemet bytes must not decode as unrelated UTF-8 code points."""

    text = _decode_qsch_bytes(b"\xdb\xabschematic\r\n")

    assert text.startswith("\xdb\xab")
    assert "\u06eb" not in text
    text.encode("cp1252")


def test_inspect_schematic_output_encodes_on_windows_cp1252(tmp_path: Path) -> None:
    schematic = tmp_path / "misdecode.qsch"
    schematic.write_bytes(
        b"".join(
            (
                b"\xdb\xabschematic\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol V\r\n",
                b"      \xabtype: V\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "V1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "5"\xbb\r\n',
                b"    \xbb\r\n",
                b"  \xbb\r\n",
            )
        )
    )

    summary = inspect_schematic(schematic, workspace_root=tmp_path)

    assert summary.component_count == 1
    assert summary.components[0].refdes == "V1"
    json.dumps(to_json_object(summary)).encode("cp1252")


def test_inspect_schematic_handles_real_example_file() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    workspace_root = repo_root
    schematic = repo_root / "tests" / "fixtures" / "schematics" / "comparator-test.qsch"
    assert schematic.is_file(), (
        f"committed fixture missing: {schematic} — it must be tracked in git so this "
        "test cannot silently skip on a clean checkout"
    )

    summary = inspect_schematic(schematic, workspace_root=workspace_root)

    assert summary.component_count > 0
    assert any(component.refdes == "X1" for component in summary.components)
    assert any(analysis.kind is AnalysisKind.TRAN for analysis in summary.analyses)


def _write_param_schematic(tmp_path: Path) -> Path:
    schematic = tmp_path / "params.qsch"
    schematic.write_bytes(
        b"".join(
            (
                b"\xabschematic\r\n",
                b"  \xabcomponent (0,0) 0 0\r\n",
                b"    \xabsymbol R\r\n",
                b"      \xabtype: R\xbb\r\n",
                b'      \xabtext (100,150) 1 7 0 0x1000000 -1 -1 "R1"\xbb\r\n',
                b'      \xabtext (100,-150) 1 7 0 0x1000000 -1 -1 "{rload}"\xbb\r\n',
                b"    \xbb\r\n",
                b'  \xabtext (0,0) 1 7 0 0x1000000 -1 -1 ".param rload=1k"\xbb\r\n',
                b'  \xabtext (0,0) 1 7 0 0x1000000 -1 -1 ".tran 5m"\xbb\r\n',
                b"\xbb\r\n",
            )
        )
    )
    return schematic


def test_inspect_schematic_optional_sections_default_off(tmp_path: Path) -> None:
    schematic = _write_param_schematic(tmp_path)

    summary = inspect_schematic(schematic, workspace_root=tmp_path)

    assert summary.parameters == ()
    assert summary.connectivity is None


def test_inspect_schematic_include_parameters_surfaces_param_directives(tmp_path: Path) -> None:
    schematic = _write_param_schematic(tmp_path)

    summary = inspect_schematic(schematic, workspace_root=tmp_path, include_parameters=True)

    assert summary.parameters == (".param rload=1k",)


def test_inspect_schematic_include_connectivity_attaches_report() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    schematic = repo_root / "tests" / "fixtures" / "schematics" / "comparator-test.qsch"
    assert schematic.is_file()

    summary = inspect_schematic(
        schematic,
        workspace_root=repo_root,
        include_connectivity=True,
    )

    assert summary.connectivity is not None
    assert summary.connectivity.component_count > 0
    assert summary.connectivity.node_count >= 0
