#!/usr/bin/env python3
"""Fix imports and format generated services/*/mcp_contracts.py files."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "src" / "qspice_mcp" / "services"

_IMPORTS = {
    "_SCALAR_VALUE": "_SCALAR_VALUE",
    "_STEP_FILTER_VALUE": "_STEP_FILTER_VALUE",
    "_STEP_FILTERS": "_STEP_FILTERS",
    "_COMPONENT": "_COMPONENT",
    "_RETAINED_ARTIFACT_POLICY": "_RETAINED_ARTIFACT_POLICY",
}


def _fix_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "MCP_CONTRACTS" not in text:
        return
    needed = [name for name in _IMPORTS if name in text and "mcp_schema_common import" not in text]
    if needed:
        import_block = (
            "from qspice_mcp.services._internals.mcp_schema_common import (\n"
            + "".join(f"    {_IMPORTS[name]},\n" for name in needed)
            + ")\n\n"
        )
        marker = "from __future__ import annotations\n\n"
        if marker in text:
            text = text.replace(marker, marker + import_block, 1)
        else:
            text = import_block + text
    path.write_text(text, encoding="utf-8")


def main() -> int:
    for path in sorted(SERVICES.rglob("mcp_contracts.py")):
        _fix_file(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
