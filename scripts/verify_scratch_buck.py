#!/usr/bin/env python3
"""Verify Track A scratch buck authoring tools through the MCP invoke_tool path."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from qspice_mcp.adapters.probe import discover_executable
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.mcp.server import create_server
from qspice_mcp.services.recipes._catalog import recipe_bundle_path

DEFAULT_WORKSPACE = Path.home() / "Desktop" / "qspice-mcp-test"
_RECIPE_ID = "buck_converter_cpp"


def _load_blueprint() -> dict[str, Any]:
    raw = recipe_bundle_path(_RECIPE_ID, "scratch_buck.blueprint.json").read_text(encoding="utf-8")
    blueprint: dict[str, Any] = json.loads(raw)
    return blueprint


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke-test Track A scratch buck authoring via MCP tools "
            "(topology preflight, workflow doc, schematic parts, optional DLL/sim)."
        )
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(os.environ.get("QSPICE_WORKSPACE_ROOT", str(DEFAULT_WORKSPACE))),
        help="Simulation workspace containing authored artifacts.",
    )
    parser.add_argument(
        "--qspice-exe",
        type=Path,
        default=None,
        help="Path to QSPICE64.exe (defaults to QSPICE_EXE env or auto-discovery).",
    )
    parser.add_argument(
        "--with-dll-build",
        action="store_true",
        help="Write bundled buck_controller.cpp and attempt auto DLL build.",
    )
    parser.add_argument(
        "--with-sim",
        action="store_true",
        help="Run dry-run simulation on the scratch schematic when QSpice is available.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output schematic filename relative to workspace.",
    )
    return parser.parse_args()


def _resolve_qspice_exe(explicit: Path | None) -> Path | None:
    if explicit is not None and explicit.is_file():
        return explicit.resolve(strict=False)
    env_path = os.environ.get("QSPICE_EXE")
    if env_path:
        candidate = Path(env_path)
        if candidate.is_file():
            return candidate.resolve(strict=False)
    discovered, _source = discover_executable(None)
    if discovered is not None and discovered.is_file():
        return discovered.resolve(strict=False)
    return None


def _result_path(payload: dict[str, object], key: str) -> Path:
    value = payload.get(key)
    if not isinstance(value, str):
        raise TypeError(f"Expected string {key}, got {payload!r}")
    return Path(value)


def _record(
    results: list[tuple[str, str, str]],
    name: str,
    ok: bool,
    detail: str,
) -> None:
    results.append((name, "PASS" if ok else "FAIL", detail))


def _check_topology_preflight(server: object, results: list[tuple[str, str, str]]) -> None:
    try:
        payload = server.invoke_tool("describe_topology_authoring_support")
        ready = payload.get("scratch_buck_ready") is True
        instruction_id = payload.get("scratch_buck_instruction_id")
        _record(
            results,
            "topology authoring preflight",
            ready and instruction_id == "buck-converter-cpp",
            f"scratch_buck_ready={payload.get('scratch_buck_ready')} "
            f"instruction_id={instruction_id!r}",
        )
    except Exception as exc:
        _record(results, "topology authoring preflight", False, str(exc))


def _check_workflow_instruction(server: object, results: list[tuple[str, str, str]]) -> None:
    try:
        payload = server.invoke_tool(
            "read_workflow_instruction",
            instruction_id="buck-converter-cpp",
        )
        content = str(payload.get("content", ""))
        ok = "add_component" in content and "nmos" in content
        _record(
            results,
            "scratch workflow instruction",
            ok,
            f"instruction_id={payload.get('instruction_id')!r} bytes={len(content)}",
        )
    except Exception as exc:
        _record(results, "scratch workflow instruction", False, str(exc))


def _build_scratch_schematic(
    server: object,
    *,
    output_name: str,
    results: list[tuple[str, str, str]],
) -> Path | None:
    blueprint = _load_blueprint()
    try:
        created = server.invoke_tool(
            "create_schematic",
            output_path=output_name,
            overwrite=True,
        )
        schematic_path = _result_path(created, "output_path")
    except Exception as exc:
        _record(results, "create scratch schematic", False, str(exc))
        return None

    schematic_name = schematic_path.name
    try:
        for block in blueprint["dll_blocks"]:
            server.invoke_tool(
                "add_dll_block",
                schematic_path=schematic_name,
                reference=block["reference"],
                device_name=block["device_name"],
                input_pin_names=list(block["input_pin_names"]),
                output_pin_names=list(block["output_pin_names"]),
                position_x=block["position_x"],
                position_y=block["position_y"],
                rotation_degrees=block["rotation_degrees"],
            )
        for component in blueprint["components"]:
            server.invoke_tool(
                "add_component",
                schematic_path=schematic_name,
                component_kind=component["kind"],
                reference=component["reference"],
                value=component["value"],
                position_x=component["position_x"],
                position_y=component["position_y"],
                rotation_degrees=component["rotation_degrees"],
            )
        for junction in blueprint["junctions"]:
            server.invoke_tool(
                "add_junction",
                schematic_path=schematic_name,
                position_x=junction["position_x"],
                position_y=junction["position_y"],
            )
        for label in blueprint["net_labels"]:
            server.invoke_tool(
                "add_net_label",
                schematic_path=schematic_name,
                position_x=label["position_x"],
                position_y=label["position_y"],
                net_name=label["net"],
            )
        for wire in blueprint["wires"]:
            server.invoke_tool(
                "add_wire",
                schematic_path=schematic_name,
                start_x=wire["start_x"],
                start_y=wire["start_y"],
                end_x=wire["end_x"],
                end_y=wire["end_y"],
                net_name=wire["net"],
            )
        for parameter in blueprint["parameters"]:
            server.invoke_tool(
                "set_parameter",
                schematic_path=schematic_name,
                name=parameter["name"],
                value=parameter["value"],
            )
        for instruction in blueprint["instructions"]:
            server.invoke_tool(
                "add_instruction",
                schematic_path=schematic_name,
                instruction=instruction,
            )
        listed = server.invoke_tool("list_components", schematic_path=schematic_name)
        references = {
            item["reference"]
            for item in listed.get("components", [])
            if isinstance(item, dict) and isinstance(item.get("reference"), str)
        }
        expected = {block["reference"] for block in blueprint["dll_blocks"]}
        expected |= {component["reference"] for component in blueprint["components"]}
        ok = references >= expected
        missing = sorted(expected - references)
        _record(
            results,
            "scratch full-buck placement",
            ok,
            f"placed={len(references)} expected={len(expected)} missing={missing}",
        )
    except Exception as exc:
        _record(results, "scratch full-buck placement", False, str(exc))
        return schematic_path
    return schematic_path


def _check_dll_build(
    server: object,
    *,
    qspice_exe: Path | None,
    results: list[tuple[str, str, str]],
) -> None:
    try:
        bundled = recipe_bundle_path(_RECIPE_ID, "buck_controller.cpp")
        content = bundled.read_text(encoding="utf-8")
        payload = server.invoke_tool(
            "write_workspace_text_file",
            relative_path="scratch_buck_controller.cpp",
            content=content,
            overwrite=True,
            build_dll_after_write=True,
        )
        if "dll_build" in payload:
            toolchain = payload.get("dll_build", {}).get("toolchain")
            output_path = payload.get("dll_build", {}).get("output_path")
            ok = isinstance(toolchain, str) and isinstance(output_path, str)
            _record(
                results,
                "scratch DLL auto-build",
                ok,
                f"toolchain={toolchain!r} output_path={output_path!r} qspice={qspice_exe}",
            )
            return
        error = payload.get("dll_build_error")
        hints = payload.get("dll_build_hints")
        suggestions = []
        if isinstance(hints, dict):
            raw = hints.get("recovery_suggestions")
            if isinstance(raw, list):
                suggestions = [str(item) for item in raw[:2]]
        detail = f"error={error!r}"
        if suggestions:
            detail += f"; hints={' | '.join(suggestions)}"
        _record(results, "scratch DLL auto-build", False, detail)
    except Exception as exc:
        _record(results, "scratch DLL auto-build", False, str(exc))


def _check_sim_dry_run(
    server: object,
    schematic_path: Path,
    results: list[tuple[str, str, str]],
) -> None:
    try:
        payload = server.invoke_tool(
            "run_simulation",
            source_path=schematic_path.name,
            dry_run=True,
        )
        ok = payload.get("dry_run") is True
        _record(
            results,
            "scratch schematic dry-run sim",
            ok,
            f"exit_code={payload.get('exit_code')} warnings={payload.get('warnings')}",
        )
    except Exception as exc:
        _record(results, "scratch schematic dry-run sim", False, str(exc))


def _print_results(results: list[tuple[str, str, str]]) -> None:
    print("Track A scratch buck verification")
    print("=" * 60)
    for name, status, detail in results:
        print(f"[{status}] {name}")
        print(f"       {detail}")


def main() -> int:
    args = _parse_args()
    workspace = args.workspace_root.expanduser().resolve(strict=False)
    workspace.mkdir(parents=True, exist_ok=True)
    qspice_exe = _resolve_qspice_exe(args.qspice_exe)
    if qspice_exe is not None:
        os.environ.setdefault("QSPICE_EXE", str(qspice_exe))

    settings = QSpiceSettings(
        exe=qspice_exe,
        workspace_root=workspace,
    )
    server = create_server(settings)
    results: list[tuple[str, str, str]] = []

    _check_topology_preflight(server, results)
    _check_workflow_instruction(server, results)

    output_name = args.output or "scratch_buck_verify.qsch"
    schematic_path = _build_scratch_schematic(
        server,
        output_name=output_name,
        results=results,
    )

    if args.with_dll_build:
        _check_dll_build(server, qspice_exe=qspice_exe, results=results)

    if args.with_sim and schematic_path is not None and qspice_exe is not None:
        _check_sim_dry_run(server, schematic_path, results)
    elif args.with_sim:
        _record(
            results,
            "scratch schematic dry-run sim",
            False,
            "skipped: QSPICE_EXE not configured",
        )

    _print_results(results)
    return 0 if all(status == "PASS" for _, status, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
