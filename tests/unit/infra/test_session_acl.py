# In the name of God, the Most Gracious, the Most Merciful
"""Tests for restricting a live GUI session directory to the current user."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.infra import session_acl
from qspice_mcp.infra.session_acl import restrict_session_directory


def test_restrict_session_directory_requires_a_directory(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="must be a directory"):
        restrict_session_directory(tmp_path / "missing")


def test_restrict_session_directory_uses_owner_mode_off_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "session"
    directory.mkdir()
    modes: list[int] = []
    monkeypatch.setattr(session_acl, "_is_windows", lambda: False)
    monkeypatch.setattr(Path, "chmod", lambda _self, mode: modes.append(mode))

    restrict_session_directory(directory)

    assert modes == [0o700]


def test_restrict_session_directory_grants_the_windows_user(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "session"
    directory.mkdir()
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(session_acl, "_is_windows", lambda: True)
    monkeypatch.setenv("USERNAME", "circuit-user")
    monkeypatch.setattr(session_acl.subprocess, "run", fake_run)

    restrict_session_directory(directory)

    assert commands[0][0] == "icacls"
    assert "/inheritance:r" in commands[0]
    assert "circuit-user:(OI)(CI)F" in commands[0]


def test_restrict_session_directory_reports_acl_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    directory = tmp_path / "session"
    directory.mkdir()
    monkeypatch.setattr(session_acl, "_is_windows", lambda: True)
    monkeypatch.delenv("USERNAME", raising=False)
    with pytest.raises(ValidationError, match="Windows user name"):
        restrict_session_directory(directory)

    monkeypatch.setenv("USERNAME", "circuit-user")
    monkeypatch.setattr(
        session_acl.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=5, stdout="", stderr="access denied"),
    )
    with pytest.raises(ValidationError, match="access denied"):
        restrict_session_directory(directory)
