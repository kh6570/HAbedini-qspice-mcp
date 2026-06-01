#!/usr/bin/env python3
"""Development MCP launcher for qspice-mcp.

Proxies stdio to ``python -m qspice_mcp`` and restarts the child when
``src/qspice_mcp`` changes. Use this as the MCP ``command`` during local
development so editable-install code edits take effect without reinstalling
the console script.

Set ``QSPICE_DEV_WATCH=0`` to disable auto-restart (single child only).
"""

from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_WATCH_ROOT = _ROOT / "src" / "qspice_mcp"
_POLL_INTERVAL_S = 0.5
_DEBOUNCE_S = 0.6


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dev stdio launcher for qspice-mcp")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=_ROOT,
        help="Workspace root passed through to qspice-mcp",
    )
    return parser.parse_args()


def _snapshot_mtimes(root: Path) -> dict[Path, float]:
    if not root.is_dir():
        return {}
    return {
        path: path.stat().st_mtime
        for path in root.rglob("*.py")
        if path.is_file()
    }


def _mtimes_changed(previous: dict[Path, float], root: Path) -> bool:
    current = _snapshot_mtimes(root)
    if set(current) != set(previous):
        return True
    return any(current[path] != previous[path] for path in current)


def _spawn_child(workspace_root: Path) -> subprocess.Popen[bytes]:
    command = [
        sys.executable,
        "-u",
        "-m",
        "qspice_mcp",
        "--workspace-root",
        str(workspace_root.resolve(strict=False)),
    ]
    return subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=os.environ.copy(),
    )


def _stderr_forwarder(proc: subprocess.Popen[bytes]) -> None:
    assert proc.stderr is not None
    for chunk in iter(lambda: proc.stderr.read(4096), b""):
        sys.stderr.buffer.write(chunk)
        sys.stderr.buffer.flush()


def _run_child(
    proc: subprocess.Popen[bytes],
    *,
    stdin_queue: queue.Queue[bytes | None],
    restart_event: threading.Event,
) -> None:
    assert proc.stdin is not None
    assert proc.stdout is not None

    stderr_thread = threading.Thread(target=_stderr_forwarder, args=(proc,), daemon=True)
    stderr_thread.start()

    def forward_stdout() -> None:
        for chunk in iter(lambda: proc.stdout.read(4096), b""):
            if restart_event.is_set():
                return
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()

    stdout_thread = threading.Thread(target=forward_stdout, daemon=True)
    stdout_thread.start()

    stdin_closed = False
    while not restart_event.is_set():
        try:
            chunk = stdin_queue.get(timeout=_POLL_INTERVAL_S)
        except queue.Empty:
            if proc.poll() is not None:
                stdout_thread.join(timeout=2.0)
                return
            continue
        if chunk is None:
            stdin_closed = True
            try:
                proc.stdin.close()
            except OSError:
                pass
            break
        try:
            proc.stdin.write(chunk)
            proc.stdin.flush()
        except (BrokenPipeError, OSError):
            stdout_thread.join(timeout=2.0)
            return

    if stdin_closed and not restart_event.is_set():
        stdout_thread.join(timeout=15.0)
        return

    stdout_thread.join(timeout=0.2)


def _watch_for_changes(
    *,
    snapshot: dict[Path, float],
    restart_event: threading.Event,
    stop_event: threading.Event,
) -> None:
    last_change = 0.0
    while not stop_event.is_set():
        time.sleep(_POLL_INTERVAL_S)
        if not _mtimes_changed(snapshot, _WATCH_ROOT):
            continue
        snapshot.clear()
        snapshot.update(_snapshot_mtimes(_WATCH_ROOT))
        last_change = time.monotonic()
        while time.monotonic() - last_change < _DEBOUNCE_S:
            if stop_event.is_set():
                return
            time.sleep(0.1)
            if _mtimes_changed(snapshot, _WATCH_ROOT):
                snapshot.clear()
                snapshot.update(_snapshot_mtimes(_WATCH_ROOT))
                last_change = time.monotonic()
        restart_event.set()
        return


def _terminate_child(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def main() -> int:
    args = _parse_args()
    watch_enabled = os.environ.get("QSPICE_DEV_WATCH", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    stdin_queue: queue.Queue[bytes | None] = queue.Queue()
    stdin_closed = threading.Event()

    def stdin_reader() -> None:
        while True:
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                stdin_closed.set()
                stdin_queue.put(None)
                return
            stdin_queue.put(chunk)

    threading.Thread(target=stdin_reader, daemon=True).start()

    snapshot: dict[Path, float] = {}
    while True:
        restart_event = threading.Event()
        stop_watch = threading.Event()
        watcher: threading.Thread | None = None

        proc = _spawn_child(args.workspace_root)

        if watch_enabled:
            snapshot = _snapshot_mtimes(_WATCH_ROOT)
            watcher = threading.Thread(
                target=_watch_for_changes,
                kwargs={
                    "snapshot": snapshot,
                    "restart_event": restart_event,
                    "stop_event": stop_watch,
                },
                daemon=True,
            )
            watcher.start()
        _run_child(proc, stdin_queue=stdin_queue, restart_event=restart_event)
        stop_watch.set()
        if watcher is not None:
            watcher.join(timeout=0.5)

        if stdin_closed.is_set():
            _terminate_child(proc)
            return 0

        if restart_event.is_set():
            _terminate_child(proc)
            sys.stderr.write(
                "[dev_qspice_mcp] source changed; restarting qspice-mcp child\n"
            )
            sys.stderr.flush()
            snapshot = _snapshot_mtimes(_WATCH_ROOT)
            continue

        _terminate_child(proc)
        return int(proc.returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
