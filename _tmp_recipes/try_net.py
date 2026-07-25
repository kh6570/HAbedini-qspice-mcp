"""Iterate netlist variants of the half/full-bridge to find a convergent config."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent / "ws_build"
EXE = os.environ.get("QSPICE_EXE", r"C:\Program Files\QSPICE\QSPICE64.exe")


def run_variant(base: str, tag: str, replacements: list[tuple[str, str]]) -> None:
    net = (WS / f"{base}.net").read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in net:
            raise SystemExit(f"pattern not found: {old!r}")
        net = net.replace(old, new)
    path = WS / f"{base}_{tag}.net"
    path.write_text(net, encoding="utf-8")
    result = subprocess.run(
        [EXE, str(path)], capture_output=True, text=True, timeout=240, cwd=WS
    )
    log = path.with_suffix(".log")
    tail = log.read_text(encoding="utf-8", errors="replace")[-400:] if log.is_file() else "(no log)"
    print(f"== {tag}: exit={result.returncode}")
    print(tail)


if __name__ == "__main__":
    base = sys.argv[1]
    tag = sys.argv[2]
    pairs = sys.argv[3:]
    reps = [(pairs[i], pairs[i + 1]) for i in range(0, len(pairs), 2)]
    run_variant(base, tag, reps)
