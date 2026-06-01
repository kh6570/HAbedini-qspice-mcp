#!/usr/bin/env python3
"""Exercise roadmap fixes through the MCP server invoke_tool path."""

from __future__ import annotations

import os
from pathlib import Path

from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server

ROOT = Path(__file__).resolve().parent.parent
TEST_WS = Path(r"C:\Users\habed\Desktop\qspice-mcp-test")
QSPICE_EXE = Path(r"C:\Program Files\QSPICE\QSPICE64.exe")


def _result_path(payload: dict[str, object], key: str) -> Path:
    value = payload.get(key)
    if not isinstance(value, str):
        raise AssertionError(f"Expected string {key}, got {payload}")
    return Path(value)


def main() -> int:
    os.environ.setdefault("QSPICE_EXE", str(QSPICE_EXE))
    TEST_WS.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, str, str]] = []

    server = create_server(QSpiceSettings(workspace_root=ROOT))

    # 1. workspace_root override for create_schematic
    stray = ROOT / "roadmap_workspace_override.qsch"
    if stray.exists():
        stray.unlink()
    try:
        created = server.invoke_tool(
            "create_schematic",
            output_path="roadmap_workspace_override.qsch",
            workspace_root=str(TEST_WS),
            overwrite=True,
        )
        output_path = _result_path(created, "output_path")
        ok = output_path.parent == TEST_WS.resolve(strict=False)
        results.append(
            (
                "create_schematic workspace_root",
                "PASS" if ok else "FAIL",
                f"output_path={output_path}",
            )
        )
        if stray.exists():
            stray.unlink()
    except Exception as exc:
        results.append(("create_schematic workspace_root", "FAIL", str(exc)))

    # 2. add_instruction description
    add_tool = next(tool for tool in server.tools if tool.name == "add_instruction")
    description = add_tool.description
    ok = "instruction=" in description and "directive or analysis" not in description
    results.append(
        (
            "add_instruction description",
            "PASS" if ok else "FAIL",
            description,
        )
    )

    test_server = create_server(QSpiceSettings(exe=QSPICE_EXE, workspace_root=TEST_WS))

    # Prepare starter schematic in test workspace
    try:
        starter = test_server.invoke_tool(
            "create_starter_schematic",
            output_path="roadmap_starter.qsch",
            overwrite=True,
            analysis_instruction=".op",
        )
        starter_path = _result_path(starter, "output_path")
    except Exception as exc:
        results.append(("setup starter schematic", "FAIL", str(exc)))
        _print_results(results)
        return 1

    # 3. inspect_schematic unicode-safe output
    try:
        inspected = test_server.invoke_tool(
            "inspect_schematic",
            schematic_path=str(starter_path.name),
        )
        ok = inspected.get("component_count", 0) > 0
        results.append(
            (
                "inspect_schematic unicode output",
                "PASS" if ok else "FAIL",
                f"components={inspected.get('component_count')}",
            )
        )
    except Exception as exc:
        results.append(("inspect_schematic unicode output", "FAIL", str(exc)))

    # 4. netlist regeneration after set_component_value
    try:
        test_server.invoke_tool(
            "set_component_value",
            schematic_path=str(starter_path.name),
            reference="R1",
            value="2.2k",
        )
        sim = test_server.invoke_tool(
            "run_simulation",
            source_path=str(starter_path.name),
            dry_run=True,
        )
        warnings = sim.get("warnings", [])
        warning_text = " ".join(str(item) for item in warnings) if isinstance(warnings, list) else ""
        netlist_path = TEST_WS / starter_path.with_suffix(".net").name
        netlist_text = netlist_path.read_text(encoding="utf-8") if netlist_path.is_file() else ""
        ok = "existing derived netlist" not in warning_text.lower() and "2.2k" in netlist_text
        results.append(
            (
                "netlist cache staleness",
                "PASS" if ok else "FAIL",
                f"warnings={warning_text!r}; has_2.2k={'2.2k' in netlist_text}",
            )
        )
    except Exception as exc:
        results.append(("netlist cache staleness", "FAIL", str(exc)))

    # 5. describe_edit_capability change_value for V1
    try:
        capability = test_server.invoke_tool(
            "describe_edit_capability",
            schematic_path=str(starter_path.name),
            reference="V1",
            intent="change_value",
        )
        ok = capability.get("supported") is True
        results.append(
            (
                "describe_edit_capability V1 change_value",
                "PASS" if ok else "FAIL",
                f"supported={capability.get('supported')} reason={capability.get('unsupported_reason')}",
            )
        )
    except Exception as exc:
        results.append(("describe_edit_capability V1 change_value", "FAIL", str(exc)))

    _print_results(results)
    return 0 if all(status == "PASS" for _, status, _ in results) else 1


def _print_results(results: list[tuple[str, str, str]]) -> None:
    print("Roadmap MCP verification")
    print("=" * 60)
    for name, status, detail in results:
        print(f"[{status}] {name}")
        print(f"       {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
