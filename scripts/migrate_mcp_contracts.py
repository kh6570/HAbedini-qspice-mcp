#!/usr/bin/env python3
"""One-shot migration: mcp/_tool_metadata -> services/*/mcp_contracts.py."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "qspice_mcp"
METADATA_DIR = SRC / "mcp" / "_tool_metadata"

_PACKAGE_BY_METADATA_FILE: dict[str, str] = {
    "artifact.py": "artifacts",
    "batch.py": "batch",
    "live_gui.py": "live_gui",
    "mixed_signal.py": "mixed_signal",
    "protocol.py": "protocol",
    "recipes.py": "recipes",
    "remote.py": "remote",
    "schematic.py": "schematic",
    "simulation.py": "simulation",
    "subcircuit.py": "subcircuit",
    "waveform.py": "waveform",
}

_WORKSPACE_TOOL_PACKAGES: dict[str, str] = {
    "write_workspace_text_file": "workspace",
    "describe_topology_authoring_support": "schematic",
    "list_workflow_instructions": "instructions",
    "read_workflow_instruction": "instructions",
}


def _strip_annotations(node: ast.expr) -> ast.expr:
    if not isinstance(node, ast.Dict):
        return node
    keys: list[ast.expr | None] = []
    values: list[ast.expr] = []
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == "annotations":
            continue
        keys.append(key)
        values.append(value)
    return ast.Dict(keys=keys, values=values)


def _extract_contract_dict(source_path: Path) -> ast.Dict:
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    for node in module.body:
        candidates: list[ast.expr | None] = []
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and (node.target.id in {"MCP_CONTRACTS"} or node.target.id.endswith("TOOL_METADATA"))
        ):
            candidates.append(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and (
                    target.id == "MCP_CONTRACTS" or target.id.endswith("TOOL_METADATA")
                ):
                    candidates.append(node.value)
        for value in candidates:
            if isinstance(value, ast.Dict):
                return value
    raise ValueError(f"{source_path}: missing MCP contract dict")


def _render_contracts(metadata_dict: ast.Dict) -> str:
    body = ast.unparse(metadata_dict)
    return (
        '"""MCP input schemas and descriptions for this service package."""\n\n'
        "from __future__ import annotations\n\n"
        "MCP_CONTRACTS: dict[str, dict[str, object]] = "
        f"{body}\n"
    )


def _rewrite_imports(content: str, metadata_source: str) -> str:
    if "_COMPONENT" in metadata_source or "_STEP_FILTERS" in metadata_source:
        content = (
            "from qspice_mcp.services._internals.mcp_schema_common import (\n"
            "    _COMPONENT,\n"
            "    _RETAINED_ARTIFACT_POLICY,\n"
            "    _SCALAR_VALUE,\n"
            "    _STEP_FILTERS,\n"
            "    _STEP_FILTER_VALUE,\n"
            ")\n\n" + content.split("\n\n", 2)[-1]
        )
    return content


def _write_contracts(package: str, metadata_dict: ast.Dict, *, metadata_source: str) -> None:
    content = _render_contracts(metadata_dict)
    content = _rewrite_imports(content, metadata_source)
    target = SRC / "services" / package / "mcp_contracts.py"
    target.write_text(content, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)}")


def _merge_contract_dicts(left: ast.Dict, right: ast.Dict) -> ast.Dict:
    keys = list(left.keys) + list(right.keys)
    values = list(left.values) + list(right.values)
    return ast.Dict(keys=keys, values=values)


def _migrate_simple(metadata_file: str, package: str) -> None:
    source = METADATA_DIR / metadata_file
    source_text = source.read_text(encoding="utf-8")
    metadata_dict = _extract_contract_dict(source)
    cleaned = ast.Dict(
        keys=list(metadata_dict.keys),
        values=[_strip_annotations(value) for value in metadata_dict.values],
    )
    _write_contracts(package, cleaned, metadata_source=source_text)


def _migrate_workspace() -> None:
    source = METADATA_DIR / "workspace.py"
    source_text = source.read_text(encoding="utf-8")
    metadata_dict = _extract_contract_dict(source)
    by_package: dict[str, list[tuple[str, ast.expr]]] = {}
    for key, value in zip(metadata_dict.keys, metadata_dict.values, strict=True):
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            raise TypeError("workspace metadata key must be string")
        tool_name = key.value
        package = _WORKSPACE_TOOL_PACKAGES[tool_name]
        by_package.setdefault(package, []).append((tool_name, _strip_annotations(value)))
    for package, entries in by_package.items():
        cleaned_dict = ast.Dict(
            keys=[ast.Constant(value=name) for name, _ in entries],
            values=[value for _, value in entries],
        )
        target = SRC / "services" / package / "mcp_contracts.py"
        if target.exists():
            existing_dict = _extract_contract_dict(target)
            cleaned_dict = _merge_contract_dicts(existing_dict, cleaned_dict)
        _write_contracts(package, cleaned_dict, metadata_source=source_text)


def main() -> int:
    for metadata_file, package in _PACKAGE_BY_METADATA_FILE.items():
        _migrate_simple(metadata_file, package)
    _migrate_workspace()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
