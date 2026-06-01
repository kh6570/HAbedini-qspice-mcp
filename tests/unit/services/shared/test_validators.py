"""Tests for service validation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from qspice_mcp.core.exceptions import (
    ArtifactMissingError,
    QSpiceError,
    SandboxViolationError,
    ValidationError,
)
from qspice_mcp.services._shared.paths import (
    resolve_workspace_path,
    validate_existing_file,
    validate_time_window,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_resolve_workspace_path_joins_relative_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    resolved = resolve_workspace_path("examples/demo.qsch", workspace_root=workspace_root)

    assert resolved == (workspace_root / "examples" / "demo.qsch").resolve()


def test_resolve_workspace_path_rejects_escape(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    outside = tmp_path / "outside.qsch"

    with pytest.raises(SandboxViolationError):
        resolve_workspace_path(outside, workspace_root=workspace_root)


def test_validate_existing_file_rejects_unexpected_suffix(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    bad_file = workspace_root / "demo.txt"
    bad_file.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError, match="Expected one of") as excinfo:
        validate_existing_file(bad_file, workspace_root=workspace_root, suffixes=(".qsch",))

    assert excinfo.value.error_code == "validation_failed"
    assert isinstance(excinfo.value, QSpiceError)
    assert isinstance(excinfo.value, ValueError)


def test_validate_existing_file_rejects_missing_file(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    missing = workspace_root / "missing.qsch"

    with pytest.raises(ArtifactMissingError, match="File not found") as excinfo:
        validate_existing_file(missing, workspace_root=workspace_root, suffixes=(".qsch",))

    assert excinfo.value.error_code == "artifact_missing"
    assert isinstance(excinfo.value, QSpiceError)


def test_validate_time_window_rejects_inverted_range() -> None:
    with pytest.raises(ValidationError, match="t_end must") as excinfo:
        validate_time_window(5.0, 1.0)

    assert excinfo.value.error_code == "validation_failed"


def test_validate_time_window_legacy_value_error_catch_still_works() -> None:
    """ValidationError multi-inherits ValueError for back-compat."""

    with pytest.raises(ValueError, match="t_end must"):
        validate_time_window(5.0, 1.0)
