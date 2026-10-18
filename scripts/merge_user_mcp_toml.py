#!/usr/bin/env python3
# In the name of God, the Most Gracious, the Most Merciful
"""Merge QSpice into ChatGPT desktop's shared Codex config, preserving comments."""

from __future__ import annotations

import argparse
import json
import tempfile
import tomllib
from pathlib import Path

import tomlkit


def merge_config(config_path: Path, server_name: str, entry: dict[str, object]) -> None:
    """Replace the selected server only; invalid existing TOML is never overwritten."""
    raw = config_path.read_text(encoding="utf-8-sig") if config_path.is_file() else ""
    document = tomlkit.parse(raw)
    servers = document.get("mcp_servers")
    if servers is None:
        servers = tomlkit.table()
        document["mcp_servers"] = servers
    if not isinstance(servers, dict):
        raise TypeError("mcp_servers must be a TOML table")

    # JSON clients require `type`; Codex infers STDIO from `command`.
    server = tomlkit.table()
    for key in ("command", "args", "env"):
        server[key] = entry[key]
    server["startup_timeout_sec"] = 30
    server["tool_timeout_sec"] = 180
    servers[server_name] = server
    rendered = tomlkit.dumps(document)
    tomllib.loads(rendered)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so interrupted setup cannot leave a partial config.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=config_path.parent, delete=False
    ) as output:
        temporary = Path(output.name)
        output.write(rendered)
    try:
        temporary.replace(config_path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_path", type=Path)
    parser.add_argument("server_name")
    parser.add_argument("entry_json_path", type=Path)
    args = parser.parse_args()
    entry = json.loads(args.entry_json_path.read_text(encoding="utf-8-sig"))
    merge_config(args.config_path, args.server_name, entry)
    print(f"updated {args.config_path} (mcp_servers.{args.server_name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
