# In the name of God, the Most Gracious, the Most Merciful
"""Restrict a live GUI session directory to the current user."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from qspice_mcp.core.exceptions import ValidationError


def restrict_session_directory(path: Path) -> None:
    """Give only the current user access to one session directory.

    On Windows this removes inherited ACEs and grants the current user full
    control. Elsewhere the directory mode is restricted to the owner.
    """

    directory = Path(path)
    if not directory.is_dir():
        raise ValidationError("Live GUI session folder must be a directory before its ACL is set.")
    if os.name != "nt":
        directory.chmod(0o700)
        return
    username = os.environ.get("USERNAME", "").strip()
    if not username:
        raise ValidationError(
            "Cannot restrict the live GUI session folder without a Windows user name."
        )
    completed = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "icacls",
            str(directory),
            "/inheritance:r",
            "/grant:r",
            f"{username}:(OI)(CI)F",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        raise ValidationError(
            "Could not restrict the live GUI session folder to the current user."
            + (f" {detail}" if detail else "")
        )


__all__ = ["restrict_session_directory"]
