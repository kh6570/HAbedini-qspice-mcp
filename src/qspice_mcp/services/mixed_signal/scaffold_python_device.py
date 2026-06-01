"""Scaffold a Python-backed custom-device server for QSPICE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._shared.paths import (
    resolve_workspace_output_path,
)
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings

_PYTHON_TEMPLATE = r'''"""QSPICE Python-backed custom device: {device_name}

See QSPICE Help > Digital/Custom Devices > Python Devices.

QSPICE launches this script as a subprocess and communicates over stdin/stdout
using a line-oriented text protocol.  The server reads pin voltages, computes
currents, and writes the result back.

Usage:
    python {safe_name}.py
"""

from __future__ import annotations

import sys
from typing import NoReturn


def compute(
    time: float,
    timestep: float,
    pins: list[float],
) -> list[float]:
    """Compute device currents from pin voltages.

    Override this function with your device behaviour.  The returned list
    must have the same length as the number of pins on the symbol.
    """
    del time, timestep, pins
    return [0.0]


# ---------------------------------------------------------------------------
# Protocol loop — normally no changes are needed below this line.
# ---------------------------------------------------------------------------

def serve() -> NoReturn:
    """Run the QSPICE Python-device protocol loop on stdin/stdout."""

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        tokens = line.strip().split()
        try:
            time = float(tokens[0])
            timestep = float(tokens[1])
            pin_voltages = [float(v) for v in tokens[2:]]
        except (ValueError, IndexError):
            break

        currents = compute(time, timestep, pin_voltages)
        response = " ".join(f"{{c:.6e}}" for c in currents)
        sys.stdout.write(response + "\n")
        sys.stdout.flush()

    sys.exit(0)


if __name__ == "__main__":
    serve()
'''


@dataclass(frozen=True, slots=True)
class PythonDeviceScaffold:
    """Metadata for one scaffolded Python-backed custom-device server."""

    device_name: str
    output_path: Path
    line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_python_device",
    title="Scaffold Python Device",
    summary=(
        "Generate a Python-backed custom-device server scaffold for the "
        "documented QSPICE Python device integration path."
    ),
    phase="implemented",
)


def scaffold_python_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    output_path: str | None = None,
) -> PythonDeviceScaffold:
    """Generate a Python-backed custom-device server scaffold."""

    del settings
    safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in device_name)
    if not safe_name:
        raise ValueError("device_name must produce a non-empty filename.")

    resolved = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=workspace_root / f"{safe_name}.py",
        suffixes=(".py",),
    )

    content = _PYTHON_TEMPLATE.format(device_name=device_name, safe_name=safe_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return PythonDeviceScaffold(
        device_name=device_name,
        output_path=resolved,
        line_count=len(content.splitlines()),
        notes=(
            f"Run: python {resolved.name}",
            "Add a 'Python Device' symbol to your schematic and set "
            f"Command=python {resolved.name}.",
        ),
    )


__all__ = ["SERVICE_SPEC", "PythonDeviceScaffold", "scaffold_python_device"]
