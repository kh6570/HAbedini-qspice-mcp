"""Scaffold a Python socket-based custom-device server for QSpice."""

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

_SOCKET_TEMPLATE = r'''"""QSpice socket-based custom device: {device_name}

See QSpice Help > Digital/Custom Devices > Socket Devices.

QSpice communicates with this server over a TCP socket.  The server reads
one line of text per timestep (pin voltages, space-separated), computes
currents, and writes one line back (currents, space-separated).

Usage:
    python {safe_name}.py --port 5555
"""

import argparse
import socket
import sys


def parse_pins(line: str) -> list[float]:
    """Parse one line of space-separated pin voltages into floats."""
    return [float(token) for token in line.strip().split()]


def compute_currents(time: float, timestep: float, pins: list[float]) -> list[float]:
    """Compute device currents from pin voltages.

    Override this function with your device behaviour.  The returned list
    must have the same length as the number of pins reported to QSpice.
    """
    del time, timestep, pins
    return [0.0]


# ---------------------------------------------------------------------------
# Server boilerplate — normally no changes are needed below this line.
# ---------------------------------------------------------------------------

def serve(port: int) -> None:
    """Run the QSpice socket-device server on the given port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(1)
        print(f"{{device_name}} socket device listening on port {{port}}", flush=True)

        while True:
            conn, addr = server.accept()
            print(f"Connected from {{addr}}", flush=True)
            with conn:
                while True:
                    line = conn.recv(4096)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    parts = text.strip().split(maxsplit=2)
                    if len(parts) < 3:
                        break
                    try:
                        time = float(parts[0])
                        timestep = float(parts[1])
                        pins = [float(v) for v in parts[2].split()]
                    except ValueError:
                        break

                    currents = compute_currents(time, timestep, pins)
                    response = " ".join(f"{{c:.6e}}" for c in currents) + "\n"
                    conn.sendall(response.encode("utf-8"))
            print("Disconnected", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"QSpice socket device: {device_name}")
    parser.add_argument("--port", type=int, required=True, help="TCP port to listen on")
    args = parser.parse_args()
    serve(args.port)
'''


@dataclass(frozen=True, slots=True)
class SocketDeviceScaffold:
    """Metadata for one scaffolded socket-based custom-device server."""

    device_name: str
    output_path: Path
    line_count: int
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_socket_device",
    title="Scaffold Socket Device",
    summary=(
        "Generate a Python socket-server scaffold for the documented QSpice "
        "socket-based custom-device workflow."
    ),
    phase="implemented",
    read_only=False,
)


def scaffold_socket_device(
    device_name: str,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    output_path: str | None = None,
) -> SocketDeviceScaffold:
    """Generate a Python socket-based custom-device server scaffold."""

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

    content = _SOCKET_TEMPLATE.format(device_name=device_name, safe_name=safe_name)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")

    return SocketDeviceScaffold(
        device_name=device_name,
        output_path=resolved,
        line_count=len(content.splitlines()),
        notes=(
            f"Run: python {resolved.name} --port 5555",
            "Add a 'Socket Device' symbol to your schematic with the matching port.",
            "QSpice sends 'time timestep Vpin1 Vpin2 ...' and expects "
            "'Ipin1 Ipin2 ...' in response.",
        ),
    )


__all__ = ["SERVICE_SPEC", "SocketDeviceScaffold", "scaffold_socket_device"]
