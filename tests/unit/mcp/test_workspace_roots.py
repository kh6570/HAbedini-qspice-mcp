"""Tests for MCP-roots workspace-root resolution helpers."""

from __future__ import annotations

from pathlib import Path

from qspice_mcp.mcp.tools.workspace import (
    choose_effective_workspace_root,
    pick_workspace_root_from_roots,
    root_uri_to_path,
)


def test_root_uri_to_path_handles_windows_drive() -> None:
    assert root_uri_to_path("file:///C:/work/space") == Path("C:/work/space")


def test_root_uri_to_path_handles_posix_path() -> None:
    assert root_uri_to_path("file:///home/user/proj") == Path("/home/user/proj")


def test_root_uri_to_path_decodes_percent_escapes() -> None:
    assert root_uri_to_path("file:///data/a%20b") == Path("/data/a b")


def test_root_uri_to_path_rejects_non_file_scheme() -> None:
    assert root_uri_to_path("https://example.com/x") is None
    assert root_uri_to_path("") is None


def test_pick_workspace_root_returns_first_existing_directory(tmp_path: Path) -> None:
    missing = (tmp_path / "missing").as_uri()
    present = tmp_path.as_uri()
    assert pick_workspace_root_from_roots([missing, present]) == tmp_path.resolve()


def test_pick_workspace_root_skips_non_directories_and_non_file_uris(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("x", encoding="utf-8")
    assert pick_workspace_root_from_roots(["https://x", file_path.as_uri()]) is None


def test_pick_workspace_root_returns_none_when_empty() -> None:
    assert pick_workspace_root_from_roots([]) is None


def test_choose_effective_workspace_root_prefers_explicit_override(tmp_path: Path) -> None:
    override = tmp_path / "override"
    configured = tmp_path / "configured"
    advertised = tmp_path / "advertised"
    chosen = choose_effective_workspace_root(
        override=override,
        configured=configured,
        process_default=tmp_path / "default",
        advertised_root=advertised,
    )
    assert chosen == override


def test_choose_effective_workspace_root_prefers_configured_over_advertised(tmp_path: Path) -> None:
    configured = tmp_path / "configured"
    advertised = tmp_path / "advertised"
    chosen = choose_effective_workspace_root(
        override=None,
        configured=configured,
        process_default=tmp_path / "default",
        advertised_root=advertised,
    )
    assert chosen == configured


def test_choose_effective_workspace_root_uses_advertised_when_configured_is_default(
    tmp_path: Path,
) -> None:
    default = tmp_path / "default"
    advertised = tmp_path / "advertised"
    chosen = choose_effective_workspace_root(
        override=None,
        configured=default,
        process_default=default,
        advertised_root=advertised,
    )
    assert chosen == advertised


def test_choose_effective_workspace_root_falls_back_to_configured(tmp_path: Path) -> None:
    default = tmp_path / "default"
    chosen = choose_effective_workspace_root(
        override=None,
        configured=default,
        process_default=default,
        advertised_root=None,
    )
    assert chosen == default
